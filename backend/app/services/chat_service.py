"""
Chat Service Abstraction

This module provides a clean abstraction layer for chat completion logic,
separating business logic from the transport layer (REST/WebSocket).
It follows the Single Responsibility Principle and DRY principles.
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from fastapi.concurrency import run_in_threadpool

from app.services.model_registry import get_model_registry
from app.chat.service import (
    ensure_conversation_exists,
    save_message,
    get_last_n_messages,
    get_conversation_summary,
    should_summarize_conversation,
    get_unsummarized_messages,
    save_conversation_summary
)
from app.memory.summary_layer import generate_conversation_summary_llm
from app.services.formatter import format_llm_response
from app.database import get_db
from app.rag.web_search import web_engine
from app.rag.processor import RAGProcessor
from app.memory.kg_manager import KGManager

logger = logging.getLogger(__name__)

# Constants
SUMMARY_THRESHOLD = 500


class ChatService:
    """Service abstraction for chat completion logic"""
    
    def __init__(
        self,
        rag_processor: Optional[RAGProcessor] = None,
        kg_manager: Optional[KGManager] = None
    ):
        self.rag_processor = rag_processor
        self.kg_manager = kg_manager
        self.model_registry = get_model_registry()
    
    @staticmethod
    def extract_file_issues_from_context(context: str) -> List[str]:
        """
        Extract file processing issues from context string.
        Returns list of issue types detected.
        """
        issues = []
        
        # Check for specific error patterns
        if "[File Processing Error" in context:
            issues.append("FILE_PROCESSING_ERROR")
        if "[File Processing Note" in context:
            issues.append("FILE_PROCESSING_NOTE")
        if "[Excel Processing Error" in context:
            issues.append("EXCEL_PROCESSING_ERROR")
        if "[Excel Processing Note" in context:
            issues.append("EXCEL_PROCESSING_NOTE")
        if "[Image Processing Note" in context:
            issues.append("IMAGE_PROCESSING_NOTE")
        if "[Error processing PDF" in context:
            issues.append("PDF_PROCESSING_ERROR")
        if "[Error processing PPTX" in context:
            issues.append("PPTX_PROCESSING_ERROR")
        if "ERROR READING FILE" in context:
            issues.append("ERROR_READING_FILE")
        if "EMPTY FILE" in context:
            issues.append("EMPTY_FILE")
        if "Files with errors" in context:
            issues.append("FILES_WITH_ERRORS")
        if "Files not found" in context:
            issues.append("FILES_NOT_FOUND")
        if "Empty files" in context:
            issues.append("EMPTY_FILES_LIST")
        
        return issues
    
    @staticmethod
    def build_prompt(
        system_prompt: str,
        conversation_summary: Optional[str],
        user_memory: str,
        last_messages: List[Dict[str, Any]],
        current_message: str,
        rag_context: Optional[str] = None,
        attached_files_context: Optional[str] = None,
        web_search_context: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Build prompt with new architecture
        """
        messages = []
        
        # System prompt
        messages.append({"role": "system", "content": system_prompt})
        
        # Conversation summary
        if conversation_summary:
            messages.append({"role": "system", "content": f"Conversation summary:\n{conversation_summary}"})
        
        # User memory (Knowledge Graph)
        if user_memory:
            messages.append({"role": "system", "content": f"Relevant User Knowledge:\n{user_memory}"})
            
        # Explicitly Attached Files (Highest Priority Context)
        if attached_files_context:
            messages.append({
                "role": "system", 
                "content": f"USER ATTACHED FILES:\n{attached_files_context}"
            })
            
        # Web Search Results (High Priority Context)
        if web_search_context:
            messages.append({
                "role": "system", 
                "content": f"CURRENT WEB SEARCH RESULTS:\n{web_search_context}"
            })
        
        # General RAG search results (Background Context)
        if rag_context:
            messages.append({"role": "system", "content": f"Background Context (Local Documents):\n{rag_context}"})
        
        # Last N messages
        for msg in last_messages:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Current message
        messages.append({"role": "user", "content": current_message})
        
        return messages
    
    async def fetch_file_context(
        self,
        file_references: List[Any],
        conversation_id: str,
        model: str,
        user_id: int
    ) -> Tuple[str, List[str]]:
        """Fetch attached file content with retry logic"""
        if not file_references or not self.rag_processor:
            return "", []
        
        try:
            # Extract filenames flexibly
            file_names = []
            for ref in file_references:
                if isinstance(ref, str):
                    file_names.append(ref)
                elif isinstance(ref, dict) and "filename" in ref:
                    file_names.append(ref["filename"])
            
            if not file_names:
                return "", []
            
            logger.info(f"Fetching content for attached files: {file_names}")
            
            # Retry loop for processing latency (Wait up to 20s)
            for attempt in range(10):
                context = await run_in_threadpool(
                    self.rag_processor.get_file_content, file_names, conversation_id
                )
                
                if context:
                    logger.info(f"Attached file content found on attempt {attempt+1}. Length: {len(context)}")
                    
                    # Check for file processing issues in the content
                    if any(issue_indicator in context for issue_indicator in [
                        "[File Processing Error",
                        "[File Processing Note",
                        "[Excel Processing Error", 
                        "[Excel Processing Note",
                        "[Image Processing Note",
                        "[Error processing PDF",
                        "[Error processing PPTX",
                        "ERROR READING FILE",
                        "EMPTY FILE",
                        "Files with errors",
                        "Files not found",
                        "Empty files"
                    ]):
                        # Extract file issues for special handling
                        issues = self.extract_file_issues_from_context(context)
                        logger.warning(f"File processing issues detected: {issues}")
                    else:
                        issues = []
                    
                    # Dynamic Truncation based on Model Context Window
                    context_window = await self.model_registry.get_model_context_window(model, user_id)
                    
                    # Reserve ~2000 tokens for system prompt, history, and response
                    # Use conservative estimate of 3 chars per token
                    safe_tokens = max(1024, context_window - 2000)
                    MAX_CONTEXT_CHARS = safe_tokens * 3
                    
                    logger.info(f"Dynamic context limit for {model} ({context_window} tokens): {MAX_CONTEXT_CHARS} chars")

                    if len(context) > MAX_CONTEXT_CHARS:
                        context = context[:MAX_CONTEXT_CHARS] + "\n\n[... Content truncated due to length limits. Please use specific questions or split the file ...]"
                        logger.warning(f"Attached file content truncated to {MAX_CONTEXT_CHARS} characters")
                    
                    return context, issues
                
                logger.info(f"Attempt {attempt+1}: File content not ready yet. Waiting 2s...")
                await asyncio.sleep(2)
            
            logger.warning(f"Timed out waiting for file content: {file_names}")
            return f"[File Processing Note: Could not retrieve content for files: {', '.join(file_names)}. The files may not have been processed yet or there was a system error.]", ["ALL_FILES_TIMEOUT"]
            
        except Exception as e:
            logger.error(f"Failed to fetch attached file content: {e}")
            return f"[File Processing Error: System error retrieving file content. Error: {str(e)}]", ["SYSTEM_ERROR"]
    
    async def fetch_web_search_context(
        self,
        message: str,
        web_search: bool,
        search_provider: str,
        user_id: int
    ) -> str:
        """Fetch web search context"""
        if not web_search:
            return ""
        
        try:
            logger.info(f"Performing blocking web search with provider: {search_provider}")
            
            # Use search_and_scrape for richer context (limit to top 3 to be fast)
            scrape_result = await web_engine.search_and_scrape(
                query=message, 
                max_results=3,
                scrape_length=2500,
                provider=search_provider,
                user_id=user_id
            )
            search_results = scrape_result.get("results", [])
            
            if search_results:
                # Add a strong directive for the LLM
                current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                context = f"CRITICAL: The following REAL-TIME WEB SEARCH RESULTS are provided as of {current_time_str}. "
                context += "You HAVE access to the internet through these results. "
                context += "Use them to provide up-to-date information. "
                context += "Do NOT use your internal training data if it conflicts with these results.\n\n"
                
                context += "Web Search Results:\n"
                for i, result in enumerate(search_results):
                    context += f"Source [{i+1}]: {result.get('title', 'No Title')}\n"
                    context += f"URL: {result.get('url', '')}\n"
                    
                    # Prioritize scraped content
                    content = result.get('scraped_content', '')
                    if content:
                        # Truncate content to avoid token overflow but keep enough for context
                        content = content[:2000]
                        context += f"Full Scraped Content: {content}\n"
                    else:
                         context += f"Snippet/Description: {result.get('description', '') or result.get('body', 'No description available.')}\n"
                    
                    context += "\n---\n"
                
                logger.info(f"Web Search Context Generated: {len(context)} chars. Results: {len(search_results)}")
                return context
            else:
                context = "Web search was attempted but returned no relevant results. Notify the user that no recent information could be found for this specific query."
                logger.warning(f"Web search returned 0 results for query: {message}")
                return context
                
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return f"Web search system error: {str(e)}"
    
    async def fetch_rag_context(
        self,
        message: str,
        conversation_id: str,
        use_rag: bool,
        file_references: List[Any]
    ) -> str:
        """Fetch RAG context"""
        # Soft Isolation: If files are explicitly attached, we prioritize them and skip general search
        # unless the user specifically asks to "search" or "find" in the message.
        should_search = use_rag and (not file_references or "search" in message.lower() or "find" in message.lower() or "compare" in message.lower())
        
        if not should_search or not self.rag_processor:
            return ""
        
        try:
            # Run in threadpool to avoid blocking event loop
            search_context = await run_in_threadpool(self.rag_processor.retrieve_context, message, conversation_id)
            return search_context
        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}")
            return ""
    
    async def fetch_memory_context(self, conversation_id: str) -> str:
        """Fetch memory context from KG"""
        if not self.kg_manager:
            return ""
        
        try:
            return self.kg_manager.get_memories(conversation_id)
        except Exception as e:
            logger.error(f"KG retrieval failed: {e}")
            return ""
    
    @staticmethod
    def smart_merge_contexts(
        file_context: str,
        web_context: str,
        rag_context: str,
        memory_context: str,
        user_message: str
    ) -> Dict[str, Any]:
        """
        Intelligently merge and prioritize different context sources.
        Returns a dict with merged_context and metadata about what was used.
        """
        # Initialize result structure
        result = {
            "merged_context": "",
            "sources_used": [],
            "priorities": {},
            "total_length": 0
        }
        
        # Define context sources with their metadata
        contexts = [
            {
                "type": "file",
                "content": file_context,
                "priority": 1,  # Highest priority - user explicitly attached files
                "weight": 1.5,
                "requires": ["has_content", "not_error"]
            },
            {
                "type": "web",
                "content": web_context,
                "priority": 2,  # High priority - real-time information
                "weight": 1.2,
                "requires": ["has_content", "not_error", "is_recent_query"]
            },
            {
                "type": "rag",
                "content": rag_context,
                "priority": 3,  # Medium priority - local knowledge
                "weight": 1.0,
                "requires": ["has_content", "not_error"]
            },
            {
                "type": "memory",
                "content": memory_context,
                "priority": 4,  # Lowest priority - background knowledge
                "weight": 0.8,
                "requires": ["has_content"]
            }
        ]
        
        # Helper functions to evaluate context quality
        def has_content(context: str) -> bool:
            return bool(context and len(context.strip()) > 10)
        
        def not_error(context: str) -> bool:
            error_indicators = [
                "Error:", "error:", "failed:", "Failed:", "cannot", "Could not",
                "not found", "Not found", "system error", "System error",
                "Processing Error", "Processing Note", "ERROR READING"
            ]
            if not context:
                return True
            return not any(indicator in context for indicator in error_indicators)
        
        def is_recent_query(message: str) -> bool:
            """Check if the query is about recent/timely information"""
            recent_keywords = [
                "today", "now", "current", "recent", "latest", "new", "update",
                "2025", "2026", "this year", "this month", "this week",
                "news", "weather", "price", "stock", "sports", "score"
            ]
            message_lower = message.lower()
            return any(keyword in message_lower for keyword in recent_keywords)
        
        # Filter and score contexts
        valid_contexts = []
        for ctx in contexts:
            # Check requirements
            requirements_met = True
            for req in ctx["requires"]:
                if req == "has_content":
                    if not has_content(ctx["content"]):
                        requirements_met = False
                        break
                elif req == "not_error":
                    if not not_error(ctx["content"]):
                        requirements_met = False
                        break
                elif req == "is_recent_query":
                    if not is_recent_query(user_message):
                        requirements_met = False
                        break
            
            if requirements_met and has_content(ctx["content"]):
                # Calculate score based on priority, weight, and content quality
                content_length = len(ctx["content"])
                score = ctx["priority"] * ctx["weight"] * (min(content_length, 5000) / 5000)
                
                valid_contexts.append({
                    "type": ctx["type"],
                    "content": ctx["content"],
                    "priority": ctx["priority"],
                    "score": score,
                    "length": content_length
                })
        
        # Sort by score (descending) and then by priority (ascending)
        valid_contexts.sort(key=lambda x: (-x["score"], x["priority"]))
        
        # Merge contexts with intelligent formatting
        merged_parts = []
        total_chars = 0
        max_total_chars = 15000  # Conservative limit to avoid token overflow
        
        for ctx in valid_contexts:
            if total_chars + ctx["length"] > max_total_chars:
                # Truncate this context to fit
                remaining_chars = max_total_chars - total_chars
                if remaining_chars > 100:  # Only include if we have meaningful space
                    truncated_content = ctx["content"][:remaining_chars] + "\n[...truncated...]"
                    merged_parts.append(f"=== {ctx['type'].upper()} CONTEXT (TRUNCATED) ===\n{truncated_content}")
                    total_chars += len(truncated_content)
                    result["sources_used"].append(f"{ctx['type']}_truncated")
                break
            else:
                # Include full context
                merged_parts.append(f"=== {ctx['type'].upper()} CONTEXT ===\n{ctx['content']}")
                total_chars += ctx["length"]
                result["sources_used"].append(ctx["type"])
            
            result["priorities"][ctx["type"]] = ctx["priority"]
        
        # Create final merged context
        if merged_parts:
            result["merged_context"] = "\n\n".join(merged_parts)
            result["total_length"] = total_chars
            
            # Add a summary header
            sources_summary = ", ".join(result["sources_used"])
            header = f"INTELLIGENT CONTEXT MERGING RESULTS:\n"
            header += f"Sources included (in priority order): {sources_summary}\n"
            header += f"Total context length: {total_chars} characters\n"
            header += "=" * 50 + "\n\n"
            
            result["merged_context"] = header + result["merged_context"]
        
        return result
    
    async def retrieve_contexts(
        self,
        message: str,
        conversation_id: str,
        user_id: int,
        file_references: List[Any],
        web_search: bool,
        search_provider: str,
        use_rag: bool,
        model: str
    ) -> Dict[str, Any]:
        """
        Retrieve all contexts in parallel.
        Returns a dictionary with all context types and metadata.
        """
        rag_context = ""
        memory_context = ""
        attached_file_context = ""
        web_search_context = ""
        file_processing_issues = []
        
        # Define async functions for each context retrieval task
        tasks = []
        if file_references and self.rag_processor:
            tasks.append(self.fetch_file_context(file_references, conversation_id, model, user_id))
        if web_search:
            tasks.append(self.fetch_web_search_context(message, web_search, search_provider, user_id))
        if use_rag and self.rag_processor:
            tasks.append(self.fetch_rag_context(message, conversation_id, use_rag, file_references))
        if self.kg_manager:
            tasks.append(self.fetch_memory_context(conversation_id))
        
        # Run all tasks concurrently
        if tasks:
            logger.info(f"Starting parallel context retrieval for {len(tasks)} tasks")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            result_index = 0
            for task_type in ["file", "web", "rag", "memory"]:
                if task_type == "file" and file_references and self.rag_processor:
                    if result_index < len(results):
                        result = results[result_index]
                        if isinstance(result, tuple):
                            attached_file_context, file_processing_issues = result
                        elif isinstance(result, Exception):
                            logger.error(f"File context task failed: {result}")
                            attached_file_context = f"[File Processing Error: {str(result)}]"
                            file_processing_issues = ["TASK_FAILED"]
                        result_index += 1
                elif task_type == "web" and web_search:
                    if result_index < len(results):
                        result = results[result_index]
                        if isinstance(result, str):
                            web_search_context = result
                        elif isinstance(result, Exception):
                            logger.error(f"Web search task failed: {result}")
                            web_search_context = f"Web search system error: {str(result)}"
                        result_index += 1
                elif task_type == "rag" and use_rag and self.rag_processor:
                    if result_index < len(results):
                        result = results[result_index]
                        if isinstance(result, str):
                            rag_context = result
                        elif isinstance(result, Exception):
                            logger.error(f"RAG task failed: {result}")
                            rag_context = ""
                        result_index += 1
                elif task_type == "memory" and self.kg_manager:
                    if result_index < len(results):
                        result = results[result_index]
                        if isinstance(result, str):
                            memory_context = result
                        elif isinstance(result, Exception):
                            logger.error(f"Memory task failed: {result}")
                            memory_context = ""
                        result_index += 1
            
            logger.info(f"Parallel context retrieval completed. File: {len(attached_file_context)} chars, Web: {len(web_search_context)} chars, RAG: {len(rag_context)} chars, Memory: {len(memory_context)} chars")
        
        # Apply smart context merging
        merged_context_result = self.smart_merge_contexts(
            file_context=attached_file_context,
            web_context=web_search_context,
            rag_context=rag_context,
            memory_context=memory_context,
            user_message=message
        )
        
        # Update contexts based on smart merging
        if merged_context_result["merged_context"]:
            # Clear individual contexts and use merged version
            attached_file_context = ""
            web_search_context = ""
            rag_context = ""
            memory_context = merged_context_result["merged_context"]
            logger.info(f"Smart context merging applied. Sources used: {merged_context_result['sources_used']}, Total length: {merged_context_result['total_length']}")
        else:
            logger.info("No valid contexts to merge, using individual contexts as-is")
        
        return {
            "rag_context": rag_context,
            "memory_context": memory_context,
            "attached_file_context": attached_file_context,
            "web_search_context": web_search_context,
            "file_processing_issues": file_processing_issues,
            "merged_context_result": merged_context_result
        }
    
    def build_system_prompt(
        self,
        deep_thinking_mode: bool = False
    ) -> str:
        """Build the system prompt for chat completion"""
        current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        system_prompt = f"""You are an AI assistant that operates in TWO MODES depending on context availability.
Current Date: {current_time_str}

────────────────────────────────────────
MODE SELECTION RULE
────────────────────────────────────────
If retrieved context, uploaded files, or WEB SEARCH RESULTS are provided in this conversation,
you MUST operate in RAG MODE.

If NO retrieved context, uploaded files, or web search results are provided,
you MUST operate in STANDARD LLM MODE.

────────────────────────────────────────
RAG MODE (Context Provided)
────────────────────────────────────────
1. PRIORITY: You MUST use the provided Context (Web Search Results or Files) as your PRIMARY source of truth.
2. OVERRIDE: If the provided Context conflicts with your internal training data, you MUST follow the Context.
3. IGNORE OLD DATA: Do NOT use your training data for real-time topics (news, prices, sports, weather). Rely ONLY on the provided "Web Search Results".
4. If web search results are provided, you MUST use them to answer real-time questions. Do NOT state you cannot access the internet.
   - Even if the search results are unstructured or messy, extract the best possible answer from them.
   - If the results contain "Sign in" or "Menu" text, ignore it and look for the article content.
5. If the answer is not fully contained in the context, respond exactly:
   "I cannot find that information in the provided context."
6. If a file is missing, unreadable, empty, or contains an error, respond exactly:
   "I cannot read the file or the file contains an error."
7. NO HALLUCINATIONS: If the specific item/data requested is not in the context, YOU MUST STATE "I cannot find [item] in the file." DO NOT substitute with other items or make up data.
8. Do NOT reveal internal reasoning.

────────────────────────────────────────
STANDARD LLM MODE (No Context)
────────────────────────────────────────
9. Answer normally using the model's general knowledge and reasoning.
10. Follow the user's instructions for tone, format, creativity, or style.
11. Do NOT mention RAG, context, or retrieval in your response."""
        
        if deep_thinking_mode:
            system_prompt += "\n\nPlease provide a detailed, step-by-step reasoning process."
        
        return system_prompt
    
    async def process_chat_completion(
        self,
        message: str,
        provider: str,
        model: str,
        client_api_key: Optional[str],
        conversation_id: Optional[str],
        user_id: int,
        show_raw_response: bool = False,
        deep_thinking_mode: bool = False,
        use_rag: bool = True,
        file_references: List[Any] = None,
        web_search: bool = False,
        search_provider: str = "duckduckgo"
    ) -> Dict[str, Any]:
        """
        Process chat completion request.
        This is the core business logic extracted from the monolithic chat_completion function.
        """
        if file_references is None:
            file_references = []
        
        logger.info(f"Chat request received. Message len: {len(message)}. Web Search: {web_search}")
        
        if not message:
            raise ValueError("Message is required")
        
        # 1. Conversation enforcement
        conversation_id = ensure_conversation_exists(conversation_id, user_id)
        
        # 2. Save user message
        metadata = {"attachments": file_references} if file_references else None
        save_message(conversation_id, user_id, "user", message, metadata, model=model, provider=provider)
        
        # 3. Context Retrieval
        contexts = await self.retrieve_contexts(
            message=message,
            conversation_id=conversation_id,
            user_id=user_id,
            file_references=file_references,
            web_search=web_search,
            search_provider=search_provider,
            use_rag=use_rag,
            model=model
        )
        
        # 4. Get History & Summary
        summary = get_conversation_summary(conversation_id)
        last_messages = get_last_n_messages(conversation_id, n=5)  # Reduced context window to prevent drift
        
        # 5. Build prompt
        system_prompt = self.build_system_prompt(deep_thinking_mode)
        
        prompt_messages = self.build_prompt(
            system_prompt=system_prompt,
            conversation_summary=summary,
            user_memory=contexts["memory_context"],
            last_messages=last_messages,
            current_message=message,
            rag_context=contexts["rag_context"],
            attached_files_context=contexts["attached_file_context"],
            web_search_context=contexts["web_search_context"]
        )
        
        # 6. ModelRegistry Execution
        strategy = self.model_registry.get_strategy(provider)
        if not strategy:
            raise ValueError(f"Unsupported provider: {provider}")
        
        api_key = client_api_key
        if not api_key:
            user_keys = self.model_registry.get_user_api_keys(user_id)
            api_key = user_keys.get(provider) or user_keys.get(strategy.get_backend_name())
        
        session = await self.model_registry.get_session()
        
        # 7. Generate response
        response_text = await strategy.generate(
            model=model, 
            messages=prompt_messages, 
            api_key=api_key, 
            session=session,
            show_raw_response=show_raw_response
        )
        
        if not show_raw_response and not deep_thinking_mode:
            try:
                response_text = format_llm_response(text=response_text, model_type=provider)
            except Exception:
                pass  # Keep original response if formatting fails

        # 8. Save assistant message
        save_message(conversation_id, user_id, "assistant", response_text, model=model, provider=provider)
        
        # 9. Prepare result
        result = {
            "response": response_text,
            "conversation_id": conversation_id,
            "context_used": {
                "has_summary": bool(summary),
                "memory_items": bool(contexts["memory_context"]),
                "last_messages": len(last_messages),
                "used_rag": bool(contexts["rag_context"]),
                "used_web_search": bool(contexts["web_search_context"])
            }
        }
        
        return result