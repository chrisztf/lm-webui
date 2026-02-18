"""
Model caching service for provider API models with SQLite persistence
Consolidated cache functions - single source of truth
"""
import sqlite3
import requests
import datetime
from typing import List, Dict, Optional, Any
from fastapi import HTTPException
from app.database import get_db


def init_model_cache():
    """Initialize the model cache table"""
    db = get_db()
    
    # Create models table for caching
    db.execute("""
        CREATE TABLE IF NOT EXISTS models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,
            model_name TEXT NOT NULL,
            last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            UNIQUE(provider, model_name)
        )
    """)
    
    # Create index for faster lookups
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_models_provider_name 
        ON models (provider, model_name)
    """)
    
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_models_last_seen 
        ON models (last_seen)
    """)
    
    db.commit()


def save_models_to_db(provider: str, models: List[str]):
    """Save models to SQLite database with upsert logic"""
    db = get_db()
    
    for model_name in models:
        db.execute("""
            INSERT INTO models (provider, model_name, last_seen, is_active)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(provider, model_name) DO UPDATE SET
                last_seen = excluded.last_seen,
                is_active = 1
        """, (provider, model_name, datetime.datetime.utcnow()))
    
    db.commit()


def get_cached_models(provider: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get cached models, optionally filtered by provider"""
    db = get_db()
    
    if provider:
        cursor = db.execute("""
            SELECT provider, model_name, last_seen, is_active 
            FROM models 
            WHERE provider = ? AND is_active = 1
            ORDER BY model_name
        """, (provider,))
    else:
        cursor = db.execute("""
            SELECT provider, model_name, last_seen, is_active 
            FROM models 
            WHERE is_active = 1
            ORDER BY provider, model_name
        """)
    
    results = cursor.fetchall()
    
    return [
        {
            "provider": row[0],
            "model_name": row[1],
            "last_seen": row[2],
            "is_active": bool(row[3])
        }
        for row in results
    ]


def update_model_cache(provider: str, model_name: str) -> None:
    """Update or insert a model in the cache"""
    db = get_db()
    
    db.execute("""
        INSERT OR REPLACE INTO models (provider, model_name, last_seen, is_active)
        VALUES (?, ?, CURRENT_TIMESTAMP, 1)
    """, (provider, model_name))
    db.commit()


def deactivate_stale_models(days_threshold: int = 7) -> int:
    """Deactivate models not seen in more than specified days"""
    db = get_db()
    
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_threshold)
    cursor = db.execute("""
        UPDATE models 
        SET is_active = 0 
        WHERE last_seen < ? AND is_active = 1
    """, (cutoff_date,))
    
    deactivated_count = cursor.rowcount
    db.commit()
    return deactivated_count


def get_model_fallback(provider: str, model_name: str) -> Optional[str]:
    """Get a fallback model if the requested one is not available"""
    db = get_db()
    
    # Try to find any active model from the same provider
    cursor = db.execute("""
        SELECT model_name 
        FROM models 
        WHERE provider = ? AND is_active = 1 
        ORDER BY last_seen DESC 
        LIMIT 1
    """, (provider,))
    
    result = cursor.fetchone()
    return result[0] if result else None


# Initialize model cache on import
init_model_cache()


def fetch_models_from_provider(provider: str, api_key: str) -> List[str]:
    """Fetch models from provider API with proper error handling"""
    if provider == "openai":
        headers = {"Authorization": f"Bearer {api_key}"}
        url = "https://api.openai.com/v1/models"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                raise HTTPException(status_code=400, detail="OpenAI API error")
            data = r.json()["data"]
            # Filter for relevant chat models
            return [m["id"] for m in data if "gpt" in m["id"]]
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"OpenAI API request failed: {str(e)}")
    
    elif provider == "grok":
        headers = {"Authorization": f"Bearer {api_key}"}
        url = "https://api.x.ai/v1/models"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                raise HTTPException(status_code=400, detail="xAI API error")
            data = r.json()["data"]
            return [m["id"] for m in data if m["id"].startswith('grok-')]
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"xAI API request failed: {str(e)}")
    
    elif provider == "anthropic" or provider == "claude":
        # Anthropic doesn't have a models endpoint, so we return common models
        # and validate them against the API
        common_models = [
            "claude-3-5-sonnet-20240620", "claude-3-5-haiku-20241022", 
            "claude-3-5-opus-20240229", "claude-3-opus-20240229",
            "claude-3-sonnet-20240229", "claude-3-haiku-20240307"
        ]
        
        # Test which models are actually available with this API key
        available_models = []
        for model in common_models:
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=api_key)
                # Test with minimal request
                client.messages.create(
                    model=model,
                    max_tokens=5,
                    messages=[{"role": "user", "content": "test"}],
                    timeout=5
                )
                available_models.append(model)
            except Exception:
                # Model not available or other error, skip it
                continue
        
        return available_models if available_models else common_models
    
    elif provider == "deepseek":
        headers = {"Authorization": f"Bearer {api_key}"}
        url = "https://api.deepseek.com/v1/models"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                raise HTTPException(status_code=400, detail="DeepSeek API error")
            data = r.json()["data"]
            return [m["id"] for m in data if m["id"].startswith('deepseek-')]
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"DeepSeek API request failed: {str(e)}")
    
    elif provider == "gemini":
        # Gemini uses Google AI API which doesn't have a standard models endpoint
        # Return common Gemini models
        return [
            "models/gemini-1.5-flash",
            "models/gemini-1.5-pro", 
            "models/gemini-1.0-pro"
        ]
    
    elif provider == "ollama":
        # Ollama models are local, fetch from local instance
        try:
            r = requests.get("http://localhost:11434/api/tags", timeout=5)
            if r.status_code != 200:
                raise HTTPException(status_code=400, detail="Ollama API error")
            data = r.json()
            return [m['name'] for m in data.get('models', [])]
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Ollama API request failed: {str(e)}")
    
    elif provider == "lmstudio":
        # LM Studio models are local, fetch from local instance
        try:
            headers = {"Authorization": "Bearer lm-studio"}
            r = requests.get("http://localhost:1234/v1/models", headers=headers, timeout=5)
            if r.status_code != 200:
                raise HTTPException(status_code=400, detail="LM Studio API error")
            data = r.json()
            return [m['id'] for m in data.get('data', [])]
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"LM Studio API request failed: {str(e)}")
    
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")


def get_models_with_fallback(provider: str, api_key: str) -> Dict:
    """
    Get models from provider API first, fallback to cached models on failure
    Returns dict with models list and source indicator
    """
    try:
        # Try to fetch from provider API first
        models = fetch_models_from_provider(provider, api_key)
        # Save successful fetch to cache
        save_models_to_db(provider, models)
        return {"models": models, "source": "live"}
    
    except Exception as e:
        # Fallback to cached models
        cached_models = get_cached_models(provider)
        if cached_models:
            return {"models": cached_models, "source": "cache"}
        else:
            # No cached models available, re-raise the original error
            raise HTTPException(status_code=500, detail=f"Failed to fetch models: {str(e)}")
