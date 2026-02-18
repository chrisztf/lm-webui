"""
Stream Normalizer

Standardizes streams from different LLM providers into a universal format.
Handles:
1. DeepSeek API (native reasoning_content)
2. Local Models (raw text with <think> tags)
3. Models that output reasoning without tags (pattern detection)
4. Split token buffering
"""
import json
import re
from typing import AsyncGenerator, Dict, Any, Optional

class StreamNormalizer:
    def __init__(self):
        self.buffer = ""
        self.inside_thought = False
        self.thought_tag_mode = False  # Track if we entered via an explicit tag
        self.active_end_tag = None     # Store the specific closing tag we're looking for
        self.has_emitted_thought_start = False
        self.reasoning_detected = False
        
        # Universal tags for different models (DeepSeek, Qwen, Gemma, etc.)
        self.thought_tags = [
            ("<think>", "</think>"),
            ("<thought>", "</thought>"),
            ("<reasoning>", "</reasoning>"),
            ("<reflection>", "</reflection>"),
            ("[think]", "[/think]"),
            ("[thought]", "[/thought]"),
            ("[reasoning]", "[/reasoning]")
        ]
        
        self.reasoning_patterns = [
            r"Let's break down the user's query step-by-step:",
            r"Step \d+:",
            r"Step \d+\.", 
            r"First,",
            r"Second,",
            r"Third,",
            r"Finally,",
            r"Analysis:",
            r"Reasoning:",
            r"Thought process:?",  # Optional colon
            r"Thought Process\n"   # Newline version seen in some models
        ]
        
        # Markers that strongly indicate the start of the final answer
        # These are only used if we are NOT in explicit tag mode
        self.final_answer_markers = [
            r"Therefore,",
            r"In conclusion,",
            r"Final answer:",
            r"Answer:",
            r"\\boxed{",
            r"\\[.*\\]"
        ]

    async def normalize_stream(self, generator: AsyncGenerator[str, None]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Takes a raw string generator and yields standardized JSON chunks.
        Output format:
        {
            "type": "stream_chunk",
            "delta": {
                "content": str | None,
                "reasoning_content": str | None
            }
        }
        """
        async for chunk in generator:
            # DEBUG: Trace raw output
            # print(f"DEBUG NORM: {chunk!r}")

            # Handle dictionary chunks (e.g. from some internal wrappers)
            if isinstance(chunk, dict):
                # If it already has reasoning_content, pass it through
                if "reasoning_content" in chunk.get("delta", {}):
                    yield {
                        "type": "stream_chunk",
                        "delta": {
                            "content": chunk["delta"].get("content"),
                            "reasoning_content": chunk["delta"].get("reasoning_content")
                        }
                    }
                    continue
                # Otherwise extract content string
                text = chunk.get("delta", {}).get("content", "") or chunk.get("content", "")
            else:
                # Raw string chunk
                text = str(chunk)

            if not text:
                continue

            self.buffer += text
            
            while self.buffer:
                if not self.inside_thought:
                    # 1. Check for universal start tags first (highest priority)
                    start_tag_found = False
                    for start_tag, end_tag in self.thought_tags:
                        start_tag_match = re.search(re.escape(start_tag), self.buffer, re.IGNORECASE)
                        if start_tag_match:
                            # Emit content before tag
                            pre_think = self.buffer[:start_tag_match.start()]
                            if pre_think:
                                yield {
                                    "type": "stream_chunk",
                                    "delta": {"content": pre_think}
                                }
                            
                            self.inside_thought = True
                            self.thought_tag_mode = True
                            self.active_end_tag = end_tag
                            self.buffer = self.buffer[start_tag_match.end():]
                            start_tag_found = True
                            break
                    
                    if start_tag_found:
                        continue

                    # 2. Check for reasoning patterns (for models that don't use tags)
                    if not self.reasoning_detected:
                        for pattern in self.reasoning_patterns:
                            pattern_match = re.search(pattern, self.buffer, re.IGNORECASE)
                            if pattern_match:
                                # Found reasoning pattern
                                self.inside_thought = True
                                self.reasoning_detected = True
                                self.thought_tag_mode = False
                                self.active_end_tag = None
                                
                                # Emit content before reasoning as regular content
                                pre_reasoning = self.buffer[:pattern_match.start()]
                                if pre_reasoning:
                                    yield {
                                        "type": "stream_chunk",
                                        "delta": {"content": pre_reasoning}
                                    }
                                self.buffer = self.buffer[pattern_match.start():]
                                break
                    
                    if not self.inside_thought:
                        # Check for partial start tag at end of buffer
                        if self._has_any_partial_start_tag(self.buffer):
                            break
                        else:
                            # Safe to emit everything
                            yield {
                                "type": "stream_chunk",
                                "delta": {"content": self.buffer}
                            }
                            self.buffer = ""
                else:
                    # INSIDE THOUGHT: Look for end marker
                    
                    # 1. Look for explicit end tag if we are in tag mode
                    end_tag_match = None
                    if self.thought_tag_mode and self.active_end_tag:
                        end_tag_match = re.search(re.escape(self.active_end_tag), self.buffer, re.IGNORECASE)
                    
                    # 2. Look for final answer markers (ONLY if NOT in strict tag mode or if we suspect tag failure)
                    earliest_marker_pos = None
                    earliest_marker_match = None
                    
                    # If we are in tag mode, we are VERY strict and ignore "Therefore," etc.
                    # because CoT models use them internally.
                    if not self.thought_tag_mode:
                        for marker in self.final_answer_markers:
                            marker_match = re.search(marker, self.buffer, re.IGNORECASE)
                            if marker_match:
                                marker_pos = marker_match.start()
                                if earliest_marker_pos is None or marker_pos < earliest_marker_pos:
                                    earliest_marker_pos = marker_pos
                                    earliest_marker_match = marker_match
                    
                    # Determine termination point
                    end_tag_pos = end_tag_match.start() if end_tag_match else None
                    
                    if end_tag_pos is not None:
                        # Explicit tag takes precedence
                        thought_content = self.buffer[:end_tag_pos]
                        if thought_content:
                            yield {
                                "type": "stream_chunk",
                                "delta": {"reasoning_content": thought_content}
                            }
                        
                        self.inside_thought = False
                        self.thought_tag_mode = False
                        self.buffer = self.buffer[end_tag_match.end():]
                        self.reasoning_detected = False
                        self.active_end_tag = None
                    elif earliest_marker_pos is not None:
                        # Pattern-based end marker
                        thought_content = self.buffer[:earliest_marker_pos]
                        if thought_content:
                            yield {
                                "type": "stream_chunk",
                                "delta": {"reasoning_content": thought_content}
                            }
                        
                        self.inside_thought = False
                        self.reasoning_detected = False
                        self.buffer = self.buffer[earliest_marker_pos:]
                    else:
                        # No end marker found yet
                        # Check for partial end tag
                        if self.thought_tag_mode and self.active_end_tag and self._has_partial_end_tag(self.buffer, self.active_end_tag):
                            # Emit safe part, keep partial tag in buffer
                            safe_len = len(self.buffer) - self._get_partial_end_tag_len(self.buffer, self.active_end_tag)
                            if safe_len > 0:
                                yield {
                                    "type": "stream_chunk",
                                    "delta": {"reasoning_content": self.buffer[:safe_len]}
                                }
                                self.buffer = self.buffer[safe_len:]
                            break
                        else:
                            # Emit everything as thought
                            yield {
                                "type": "stream_chunk",
                                "delta": {"reasoning_content": self.buffer}
                            }
                            self.buffer = ""

    def _has_any_partial_start_tag(self, text: str) -> bool:
        """Check if text ends with any partial start tag"""
        for start_tag, _ in self.thought_tags:
            for i in range(1, len(start_tag)):
                if text.endswith(start_tag[:i]):
                    return True
        return False

    def _has_partial_end_tag(self, text: str, end_tag: str) -> bool:
        """Check if text ends with partial specific end tag"""
        for i in range(1, len(end_tag)):
            if text.endswith(end_tag[:i]):
                return True
        return False

    def _get_partial_end_tag_len(self, text: str, end_tag: str) -> int:
        """Get length of partial specific end tag at end"""
        for i in range(len(end_tag) - 1, 0, -1):
            if text.endswith(end_tag[:i]):
                return i
        return 0

