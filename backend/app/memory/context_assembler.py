"""
Context Assembler
Unifies context retrieval from Summary, Knowledge Graph, Vector Memory, and RAG.
Updated for new RAG architecture.
"""
import logging
from typing import Dict, Any, List, Optional
from app.memory.summary_layer import get_conversation_summary
from app.memory.kg_manager import KGManager
# from app.memory.vector_memory import vector_memory # Legacy vector memory disabled
from app.chat.service import get_last_n_messages
# New RAG
from app.rag.processor import RAGProcessor

logger = logging.getLogger(__name__)

# Initialize RAG Processor (Singleton)
try:
    rag_processor = RAGProcessor()
except Exception as e:
    logger.error(f"Failed to init RAGProcessor in context assembler: {e}")
    rag_processor = None

# Initialize KGManager
try:
    import os
    data_dir = os.getenv("DATA_DIR")
    if data_dir:
        if os.path.isabs(data_dir):
             mem_path = os.path.join(data_dir, "memory", "memory.db")
        else:
             base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
             mem_path = os.path.join(base_dir, data_dir, "memory", "memory.db")
    else:
         base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
         mem_path = os.path.join(base_dir, "data", "memory", "memory.db")
         
    kg_manager = KGManager(mem_path)
except Exception as e:
    logger.error(f"Failed to init KGManager in context assembler: {e}")
    kg_manager = None

class ContextAssembler:
    """Service to assemble comprehensive context for LLM generation"""
    
    async def assemble_context(
        self, 
        user_id: int, 
        conversation_id: str, 
        query: str,
        use_rag: bool = False
    ) -> Dict[str, Any]:
        """
        Gather context from all sources
        """
        context = {
            "summary": None,
            "recent_messages": [],
            "relevant_history": [],
            "relevant_knowledge": [],
            "rag_chunks": []
        }
        
        # 1. Rolling Summary (Fast SQL)
        context["summary"] = get_conversation_summary(conversation_id)
        
        # 2. Recent History (Fast SQL)
        context["recent_messages"] = get_last_n_messages(conversation_id, n=10)
        
        # 3. Relevant History (Vector Search) - DISABLED/STUBBED
        # Old vector_memory used legacy RAG stack. 
        # For now, we rely on recent_messages. 
        # Future: Implement history vector search using RAGProcessor or similar?
        pass 
            
        # 4. Relevant Knowledge (Vector Search on KG -> Simple Search now)
        try:
            # search_memories returns list of dicts
            kg_results = []
            if kg_manager:
                kg_results = kg_manager.search_memories(query, user_id=user_id, limit=5)
            context["relevant_knowledge"] = kg_results
        except Exception as e:
            logger.warning(f"KG search failed: {e}")
            
        # 5. RAG Documents (New System)
        if use_rag and rag_processor:
            try:
                # Retrieve context string
                rag_text = rag_processor.retrieve_context(query, conversation_id)
                if rag_text:
                    # Wrap in a chunk structure for compatibility with existing format logic
                    context["rag_chunks"] = [{
                        "content": rag_text,
                        "metadata": {"filename": "RAG Context"}
                    }]
            except Exception as e:
                logger.warning(f"RAG search failed: {e}")
                
        return context

    def format_context_string(self, context: Dict[str, Any]) -> str:
        """Format the assembled context into a prompt string"""
        parts = []
        
        # Summary
        if context["summary"]:
            parts.append(f"Conversation Summary:\n{context['summary']}")
            
        # Knowledge
        if context["relevant_knowledge"]:
            parts.append("Relevant User Knowledge:")
            for item in context["relevant_knowledge"]:
                parts.append(f"- {item.get('content')} (Confidence: {item.get('confidence', 0):.2f})")
        
        # Relevant Past History
        if context["relevant_history"]:
            parts.append("Relevant Past Conversation Context:")
            for item in context["relevant_history"]:
                content = item.get("content", "")
                if content:
                    parts.append(f"- {content}")
                    
        # RAG Documents
        if context["rag_chunks"]:
            parts.append("Relevant Document Context:")
            for chunk in context["rag_chunks"]:
                # filename = chunk.get("metadata", {}).get("filename", "Unknown")
                content = chunk.get("content", "").strip()
                parts.append(f"{content}")
            
        return "\n\n".join(parts)

# Global instance
context_assembler = ContextAssembler()
