"""
Reasoning Parser for Interactive Chat

Parses structured reasoning from AI model outputs and converts them
into interactive events for frontend display.
"""
import re
import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from ..events import (
    EventType, StreamingEvent, ReasoningStep,
    SearchEvent, CodeEvent, CalculationEvent, TextEvent,
    create_session_start_event, create_final_answer_event,
    create_error_event, create_cancelled_event
)


class ReasoningStepInfo:
    """Represents a single reasoning step"""

    def __init__(
        self,
        step_index: int,
        content: str,
        step_type: str = "inference",
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.step_index = step_index
        self.content = content
        self.step_type = step_type
        self.title = title or f"Step {step_index}: {step_type.title()}"
        self.metadata = metadata or {}
        self.timestamp = datetime.now().timestamp()


class ReasoningBuilder:
    """Builds structured reasoning from text chunks"""

    def __init__(self, web_search_manager=None):
        self.steps: List[ReasoningStepInfo] = []
        self.current_step_index = 0
        self.parsed_events: List[Dict[str, Any]] = []
        self.web_search_manager = web_search_manager

    async def add_text_chunk(self, text: str, session_id: Optional[str] = None) -> List[StreamingEvent]:
        """Parse reasoning from incoming text chunk and return events"""
        events = []

        # Parse structured reasoning markers
        reasoning_events = self._parse_structured_reasoning(text)

        for event_data in reasoning_events:
            event_type = event_data["type"]
            content = event_data["content"]
            metadata = event_data.get("metadata", {})

            if event_type == EventType.REASONING_STEP:
                self.current_step_index += 1
                step = ReasoningStepInfo(
                    step_index=self.current_step_index,
                    content=content,
                    step_type=metadata.get("step_type", "inference"),
                    title=metadata.get("title"),
                    metadata=metadata
                )
                self.steps.append(step)

                # Create reasoning step event
                event = ReasoningStep(
                    content=step.content,
                    step_index=step.step_index,
                    step_type=step.step_type,
                    title=step.title,
                    metadata=step.metadata,
                    session_id=session_id
                )
                events.append(event)

            elif event_type == EventType.SEARCH_START:
                event = SearchEvent(
                    event_type=EventType.SEARCH_START,
                    query=content,
                    session_id=session_id
                )
                events.append(event)

                # Perform actual web search and scraping if web_search_manager is available
                if self.web_search_manager:
                    try:
                        # Perform search and scrape top results
                        search_results = await self.web_search_manager.scraper.search_and_scrape(
                            query=content,
                            max_results=3,
                            content_length=2000
                        )

                        if search_results.get("success"):
                            # Create search result event with actual data
                            result_event = SearchEvent(
                                event_type=EventType.SEARCH_RESULT,
                                query=content,
                                results=search_results.get("results", []),
                                session_id=session_id
                            )
                            events.append(result_event)
                        else:
                            # Create error event if search failed
                            error_event = SearchEvent(
                                event_type=EventType.SEARCH_RESULT,
                                query=content,
                                results=[],
                                session_id=session_id
                            )
                            # Add error metadata
                            error_event.metadata = {"error": search_results.get("error", "Search failed")}
                            events.append(error_event)
                    except Exception as search_error:
                        # Create error event for search failures
                        error_event = SearchEvent(
                            event_type=EventType.SEARCH_RESULT,
                            query=content,
                            results=[],
                            session_id=session_id
                        )
                        error_event.metadata = {"error": str(search_error)}
                        events.append(error_event)
                else:
                    # Fallback to mock results if no web search manager
                    mock_results = [{
                        "title": f"Search result for: {content}",
                        "url": f"https://example.com/search?q={content.replace(' ', '+')}",
                        "snippet": f"Found information related to: {content}"
                    }]
                    event = SearchEvent(
                        event_type=EventType.SEARCH_RESULT,
                        query=content,
                        results=mock_results,
                        session_id=session_id
                    )
                    events.append(event)

            elif event_type == EventType.CODE_EXECUTION:
                event = CodeEvent(
                    event_type=EventType.CODE_EXECUTION,
                    code=content,
                    language=metadata.get("language", "python"),
                    session_id=session_id
                )
                events.append(event)

                # Mock code execution result
                mock_output = self._simulate_code_execution(content)
                result_event = CodeEvent(
                    event_type=EventType.CODE_RESULT,
                    code=content,
                    language=metadata.get("language", "python"),
                    output=mock_output,
                    session_id=session_id
                )
                events.append(result_event)

            elif event_type == EventType.CALCULATION:
                event = CalculationEvent(
                    event_type=EventType.CALCULATION,
                    expression=content,
                    session_id=session_id
                )
                events.append(event)

                # Mock calculation result
                mock_result = self._simulate_calculation(content)
                result_event = CalculationEvent(
                    event_type=EventType.CALCULATION_RESULT,
                    expression=content,
                    result=mock_result,
                    session_id=session_id
                )
                events.append(result_event)

        # If no structured events found, create text events
        if not events:
            # Check if this looks like final answer
            if self._is_final_answer(text):
                event = create_final_answer_event(text, session_id)
            else:
                # Regular text chunk
                event = TextEvent(text, session_id=session_id)

            events.append(event)

        return events

    def _parse_structured_reasoning(self, text: str) -> List[Dict[str, Any]]:
        """Parse structured reasoning markers from text"""
        events = []

        # Pattern for JSON-like blocks in reasoning
        json_patterns = [
            r'\{[^{}]*"reasoning_step"[^{}]*\}',
            r'\{[^{}]*"step"[^{}]*\}',  # Alternative format
            r'\{[^{}]*"search"[^{}]*\}',
            r'\{[^{}]*"calculation"[^{}]*\}',
            r'\{[^{}]*"code"[^{}]*\}',
            r'\{[^{}]*"execute"[^{}]*\}'  # Alternative for code
        ]

        for pattern in json_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                json_str = match.group()
                try:
                    data = json.loads(json_str)

                    # Normalize different possible keys
                    if "reasoning_step" in data or data.get("step") == "reasoning":
                        content = data.get("reasoning_step") or data.get("content", "")
                        events.append({
                            "type": EventType.REASONING_STEP,
                            "content": content,
                            "metadata": {
                                "step_type": data.get("type", "inference"),
                                "title": data.get("title")
                            }
                        })

                    elif "search" in data:
                        content = data.get("query", data["search"])
                        events.append({
                            "type": EventType.SEARCH_START,
                            "content": content
                        })

                    elif "calculation" in data:
                        content = data.get("expression", data["calculation"])
                        events.append({
                            "type": EventType.CALCULATION,
                            "content": content
                        })

                    elif "code" in data or "execute" in data:
                        content = data.get("code") or data.get("execute", "")
                        events.append({
                            "type": EventType.CODE_EXECUTION,
                            "content": content,
                            "metadata": {
                                "language": data.get("language", "python")
                            }
                        })

                except json.JSONDecodeError:
                    continue

        return events

    def _is_final_answer(self, text: str) -> bool:
        """Check if text contains final answer markers"""
        final_markers = [
            "final answer",
            "conclusion:",
            "therefore,",
            "in conclusion",
            "{final_answer:",
            "[final answer]"
        ]

        text_lower = text.lower()
        return any(marker in text_lower for marker in final_markers)

    def _simulate_code_execution(self, code: str) -> str:
        """Mock code execution for demonstration"""
        # Basic pattern matching for simple examples
        if "print(" in code:
            # Extract what's being printed
            match = re.search(r'print\(["\']([^"\']+)["\']', code)
            if match:
                return match.group(1)

        if "2 + 2" in code or "2+2" in code:
            return "4"

        # Default response
        return "Code executed successfully"

    def _simulate_calculation(self, expression: str) -> str:
        """Mock calculation for demonstration"""
        expression = expression.strip()

        # Very basic math evaluation for demonstration
        try:
            # Only allow safe operations
            if any(char in expression for char in ['=', ';', 'import', 'exec', 'eval']):
                return "Calculation not allowed"

            # Simple arithmetic
            if "+" in expression and not any(op in expression for op in ['/', '//', '**', '%']):
                parts = expression.split("+")
                if len(parts) == 2:
                    try:
                        a, b = float(parts[0]), float(parts[1])
                        return str(a + b)
                    except ValueError:
                        pass

            # Basic known results
            known_results = {
                "2+2": "4",
                "5*3": "15",
                "10/2": "5"
            }

            return known_results.get(expression.replace(" ", ""), "42")

        except Exception:
            return "Unable to calculate"


class ReasoningParser:
    """Main reasoning parser for processing AI outputs"""

    def __init__(self, web_search_manager=None):
        self.builders: Dict[str, ReasoningBuilder] = {}
        self.web_search_manager = web_search_manager

    def start_reasoning_session(self, session_id: str) -> None:
        """Start a new reasoning session"""
        self.builders[session_id] = ReasoningBuilder(self.web_search_manager)

    async def process_text_chunk(
        self,
        session_id: str,
        text: str
    ) -> List[StreamingEvent]:
        """Process text chunk and return streaming events"""
        if session_id not in self.builders:
            self.start_reasoning_session(session_id)

        builder = self.builders[session_id]
        return await builder.add_text_chunk(text, session_id)

    def finish_reasoning_session(self, session_id: str) -> Dict[str, Any]:
        """Finish reasoning session and return summary"""
        if session_id in self.builders:
            builder = self.builders[session_id]

            # Create summary
            summary = {
                "total_steps": len(builder.steps),
                "step_types": {},
                "duration": None
            }

            # Count step types
            for step in builder.steps:
                step_type = step.step_type
                summary["step_types"][step_type] = summary["step_types"].get(step_type, 0) + 1

            # Calculate duration
            if builder.steps:
                start_time = builder.steps[0].timestamp
                end_time = builder.steps[-1].timestamp
                summary["duration"] = end_time - start_time

            return summary

        return {"total_steps": 0, "step_types": {}, "duration": None}

    def cancel_reasoning_session(self, session_id: str) -> bool:
        """Cancel reasoning session"""
        if session_id in self.builders:
            del self.builders[session_id]
            return True
        return False

    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get information about a reasoning session"""
        if session_id not in self.builders:
            return {"status": "not_found"}

        builder = self.builders[session_id]
        return {
            "status": "active",
            "steps_count": len(builder.steps),
            "current_step_index": builder.current_step_index,
            "last_activity": builder.steps[-1].timestamp if builder.steps else None
        }


# Singleton instance
reasoning_parser = ReasoningParser()


# Convenience functions
def start_reasoning_session(session_id: str) -> None:
    """Start a new reasoning session"""
    reasoning_parser.start_reasoning_session(session_id)


async def process_reasoning_chunk(session_id: str, text: str) -> List[StreamingEvent]:
    """Process text chunk through reasoning parser"""
    return await reasoning_parser.process_text_chunk(session_id, text)


def finish_reasoning_session(session_id: str) -> Dict[str, Any]:
    """Finish reasoning session and get summary"""
    return reasoning_parser.finish_reasoning_session(session_id)


def cancel_reasoning_session(session_id: str) -> bool:
    """Cancel reasoning session"""
    return reasoning_parser.cancel_reasoning_session(session_id)
