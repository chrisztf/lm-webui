"""
Reasoning Formatters for Frontend Display

Transforms reasoning events into formats optimized for frontend consumption,
supporting interactive displays similar to Grok and DeepSeek.
"""
from typing import Dict, List, Any, Optional, Union
from ..events import StreamingEvent, EventType


def format_reasoning_for_frontend(event: StreamingEvent) -> Dict[str, Any]:
    """
    Format a streaming event for frontend consumption

    Converts backend event structures into frontend-friendly formats
    with additional UI metadata.
    """
    base_format = {
        "id": f"{event.type}_{event.timestamp}",
        "type": event.type,
        "timestamp": event.timestamp,
        "content": event.content,
        "session_id": event.session_id,
        "step_index": event.step_index,
        "metadata": event.metadata or {},
        "ui": _get_ui_metadata(event)
    }

    # Add type-specific formatting
    if event.type == EventType.REASONING_STEP:
        base_format.update(_format_reasoning_step(event))
    elif event.type in [EventType.SEARCH_START, EventType.SEARCH_RESULT]:
        base_format.update(_format_search_event(event))
    elif event.type in [EventType.CODE_EXECUTION, EventType.CODE_RESULT]:
        base_format.update(_format_code_event(event))
    elif event.type in [EventType.CALCULATION, EventType.CALCULATION_RESULT]:
        base_format.update(_format_calculation_event(event))
    elif event.type in [EventType.TEXT_CHUNK, EventType.TEXT_COMPLETE]:
        base_format.update(_format_text_event(event))

    return base_format


def _get_ui_metadata(event: StreamingEvent) -> Dict[str, Any]:
    """Get UI-specific metadata for event rendering"""
    ui_metadata = {
        "show_expanded": True,  # Default to expanded
        "allow_interaction": True,
        "background_color": "#ffffff",
        "border_color": "#e0e0e0",
        "icon": "default"
    }

    # Customize based on event type
    if event.type == EventType.REASONING_STEP:
        ui_metadata.update({
            "show_expanded": False,  # Collapse by default for lengthy content
            "background_color": "#f8f9ff",
            "border_color": "#0066cc",
            "icon": "brain"
        })
    elif event.type in [EventType.SEARCH_START, EventType.SEARCH_RESULT]:
        ui_metadata.update({
            "background_color": "#fff8f0",
            "border_color": "#ff6600",
            "icon": "search"
        })
    elif event.type in [EventType.CODE_EXECUTION, EventType.CODE_RESULT]:
        ui_metadata.update({
            "background_color": "#f8fff8",
            "border_color": "#009900",
            "icon": "terminal"
        })
    elif event.type in [EventType.CALCULATION, EventType.CALCULATION_RESULT]:
        ui_metadata.update({
            "background_color": "#f8f8ff",
            "border_color": "#660099",
            "icon": "calculator"
        })
    elif event.type == EventType.FINAL_ANSWER:
        ui_metadata.update({
            "background_color": "#fff8f8",
            "border_color": "#cc0000",
            "icon": "check-circle"
        })
    elif event.type == EventType.ERROR:
        ui_metadata.update({
            "background_color": "#fff0f0",
            "border_color": "#cc0000",
            "icon": "alert-triangle"
        })
    elif event.type == EventType.CANCELLED:
        ui_metadata.update({
            "background_color": "#fff5f5",
            "border_color": "#996600",
            "icon": "x-circle"
        })

    return ui_metadata


def _format_reasoning_step(event: StreamingEvent) -> Dict[str, Any]:
    """Format reasoning step for frontend"""
    metadata = event.metadata or {}

    return {
        "step_type": metadata.get("step_type", "inference"),
        "step_title": metadata.get("title", f"Reasoning Step"),
        "confidence_score": metadata.get("confidence", 0.8),
        "alternative_explanations": metadata.get("alternatives", []),
        "evidence_count": metadata.get("evidence_count", 0),
        "reasoning_depth": metadata.get("depth", 1),
        "actions": [
            {"label": "Show Full Reasoning", "action": "expand"},
            {"label": "Continue From Here", "action": "continue"},
            {"label": "Branch Conversation", "action": "branch"}
        ]
    }


def _format_search_event(event: StreamingEvent) -> Dict[str, Any]:
    """Format search event for frontend"""
    metadata = event.metadata or {}

    formatted = {
        "query": metadata.get("query", ""),
        "results_count": metadata.get("results_count", 0),
        "search_engine": metadata.get("engine", "web"),
        "actions": [
            {"label": "View Results", "action": "expand"},
            {"label": "Search Deeper", "action": "search_deeper"}
        ]
    }

    # Add detailed results if available
    if event.type == EventType.SEARCH_RESULT and metadata.get("results"):
        formatted["results"] = [
            {
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "snippet": result.get("snippet", ""),
                "relevance_score": result.get("score", 0.8)
            }
            for result in metadata["results"]
        ]

    return formatted


def _format_code_event(event: StreamingEvent) -> Dict[str, Any]:
    """Format code execution event for frontend"""
    metadata = event.metadata or {}

    formatted = {
        "language": metadata.get("language", "python"),
        "has_output": bool(metadata.get("output")),
        "execution_time": metadata.get("execution_time"),
        "success": metadata.get("success", True),
        "actions": [
            {"label": "View Code", "action": "expand"},
            {"label": "Copy Code", "action": "copy"},
            {"label": "Re-run", "action": "rerun"}
        ]
    }

    # Add code highlighting info if output exists
    if metadata.get("output"):
        formatted["output_lines"] = len(metadata["output"].split('\n'))
        formatted["has_errors"] = "error" in metadata["output"].lower()

    return formatted


def _format_calculation_event(event: StreamingEvent) -> Dict[str, Any]:
    """Format calculation event for frontend"""
    metadata = event.metadata or {}

    formatted = {
        "expression": metadata.get("expression", ""),
        "result": metadata.get("result"),
        "steps": metadata.get("steps", []),
        "calculation_type": metadata.get("type", "arithmetic"),
        "precision": metadata.get("precision", 2),
        "actions": [
            {"label": "Show Steps", "action": "expand"},
            {"label": "Verify Result", "action": "verify"}
        ]
    }

    return formatted


def _format_text_event(event: StreamingEvent) -> Dict[str, Any]:
    """Format text content event for frontend"""
    metadata = event.metadata or {}

    return {
        "word_count": metadata.get("word_count", 0),
        "char_count": metadata.get("char_count", 0),
        "is_complete": metadata.get("is_complete", False),
        "sentences": metadata.get("sentence_count"),
        "actions": [
            {"label": "Read Aloud", "action": "tts"},
            {"label": "Translate", "action": "translate"}
        ]
    }


def format_reasoning_session_summary(
    session_id: str,
    summary: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Format reasoning session summary for frontend display

    Used when a streaming session finishes to show analytics.
    """
    return {
        "session_id": session_id,
        "total_steps": summary.get("total_steps", 0),
        "duration_seconds": summary.get("duration"),
        "step_distribution": summary.get("step_types", {}),
        "metrics": {
            "avg_steps_per_minute": _calculate_steps_per_minute(summary),
            "most_used_step_type": _get_most_used_step_type(summary),
            "reasoning_depth": _estimate_reasoning_depth(summary)
        },
        "insights": _generate_reasoning_insights(summary)
    }


def _calculate_steps_per_minute(summary: Dict[str, Any]) -> float:
    """Calculate reasoning speed"""
    total_steps = summary.get("total_steps", 0)
    duration = summary.get("duration", 1)  # Avoid division by zero

    if duration <= 0:
        return 0.0

    return (total_steps / duration) * 60


def _get_most_used_step_type(summary: Dict[str, Any]) -> str:
    """Get the most frequently used reasoning step type"""
    step_types = summary.get("step_types", {})

    if not step_types:
        return "unknown"

    return max(step_types.items(), key=lambda x: x[1])[0]


def _estimate_reasoning_depth(summary: Dict[str, Any]) -> int:
    """Estimate reasoning complexity based on step types"""
    step_types = summary.get("step_types", {})

    # Code and calculations suggest deeper reasoning
    depth_score = (
        step_types.get("code", 0) * 3 +
        step_types.get("calculation", 0) * 2 +
        step_types.get("search", 0) * 2 +
        step_types.get("inference", 0)
    )

    # Convert to 1-5 scale
    return min(5, max(1, depth_score // 5 + 1))


def _generate_reasoning_insights(summary: Dict[str, Any]) -> List[str]:
    """Generate natural language insights about the reasoning session"""
    insights = []

    total_steps = summary.get("total_steps", 0)
    duration = summary.get("duration", 0)
    step_types = summary.get("step_types", {})

    if total_steps > 10:
        insights.append(f"This was a thorough analysis with {total_steps} reasoning steps")

    if duration > 30:
        insights.append("The AI took time to explore multiple possibilities")

    if step_types.get("search", 0) > step_types.get("inference", 0):
        insights.append("This reasoning relied heavily on external information gathering")

    if step_types.get("code", 0) > 0:
        insights.append("The reasoning included programmatic verification")

    return insights or ["Reasoning analysis completed"]


def batch_format_events(events: List[StreamingEvent]) -> List[Dict[str, Any]]:
    """Format multiple events for efficient frontend consumption"""
    return [format_reasoning_for_frontend(event) for event in events]


def create_live_reasoning_ui_state(
    session_id: str,
    current_events: List[StreamingEvent],
    session_summary: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create complete UI state for live reasoning display

    This bundles all necessary data for rendering the Grok-style reasoning UI.
    """
    formatted_events = batch_format_events(current_events)

    ui_state = {
        "session_id": session_id,
        "events": formatted_events,
        "is_active": True,
        "controls": {
            "can_stop": True,
            "can_continue": True,
            "can_branch": True,
            "can_export": False  # Enable when session finishes
        },
        "stats": {
            "total_events": len(formatted_events),
            "reasoning_steps": len([e for e in formatted_events if e["type"] == EventType.REASONING_STEP]),
            "start_time": formatted_events[0]["timestamp"] if formatted_events else None
        },
        "viewport": {
            "scroll_to_bottom": True,
            "show_latest_events": True,
            "highlight_new_events": True
        }
    }

    # Add summary if session is complete
    if session_summary:
        ui_state.update({
            "is_active": False,
            "controls": {
                "can_stop": False,
                "can_continue": False,
                "can_branch": True,
                "can_export": True
            },
            "summary": format_reasoning_session_summary(session_id, session_summary)
        })

    return ui_state
