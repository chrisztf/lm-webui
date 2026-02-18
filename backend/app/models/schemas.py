# === backend/app/models/schemas.py ===
from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    message: str
    provider: str  # 'ollama', 'openai', 'grok', 'claude', 'lmstudio'
    model: str
    api_key: Optional[str] = None
    endpoint: Optional[str] = None  # For configurable endpoints like LM Studio
    conversation_history: Optional[list] = None  # List of previous messages for context
    show_raw_response: bool = False  # Show raw unfiltered model output
    deep_thinking_mode: bool = False  # Enable extended reasoning/deep thinking
    user_id: Optional[int] = None  # User ID for context and auto-save
    conversation_id: Optional[str] = None  # Conversation ID for organization


class ModelsResponse(BaseModel):
    models: List[str]
    source: str  # 'live' or 'cache'
