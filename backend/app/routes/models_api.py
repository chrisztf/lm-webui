"""
API Models Routes

This module provides routes for API-based model management from external providers.
Requires authentication for all endpoints.
"""

from fastapi import APIRouter, Depends, Query, Request, HTTPException
from app.security.auth.dependencies import get_current_user
from app.services.model_registry import get_model_registry

router = APIRouter(prefix="/api/models/api")

@router.get("")
async def list_api_models(provider: str = Query(None), user_id: dict = Depends(get_current_user)):
    """Get API models for authenticated user, optionally filtered by provider"""
    model_registry = get_model_registry()
    
    # Debug: Check what models we have before filtering
    print(f"DEBUG: API models route - Provider filter: {provider}")
    
    # Fetch models using ModelRegistry
    models = await model_registry.fetch_models_for_user(user_id["id"])
    
    print(f"DEBUG: Total models before filtering: {len(models)}")
    print(f"DEBUG: Available providers: {list(set(m.get('provider') for m in models))}")

    # Map frontend provider names to backend names for filtering
    # Accept both 'google' and 'gemini' as input, but always return 'google'
    provider_mapping = {
        'gemini': 'google',  # Accept 'gemini' from frontend, map to 'google' for backend
        'claude': 'anthropic',
        'grok': 'xai'
    }
    
    # Filter by provider if specified
    if provider:
        # Map frontend provider to backend provider for filtering
        backend_provider = provider_mapping.get(provider, provider)
        filtered_models = [model for model in models if model.get("provider") == backend_provider]
        print(f"DEBUG: Models after filtering for provider '{provider}' (backend: '{backend_provider}'): {len(filtered_models)}")
        
        formatted_models = []
        for model in filtered_models:
            # Always return 'google' as provider name for Google models
            # This standardizes frontend provider naming
            model_provider = model.get("provider", "unknown")
            response_provider = "google" if model_provider == "google" else model_provider
            formatted_models.append({
                "id": model.get("id", model.get("name", "unknown")),
                "name": model.get("name", model.get("id", "unknown")),
                "provider": response_provider
            })
        return {"models": formatted_models}

    # Format all models with standardized provider names
    formatted_models = []
    for model in models:
        model_provider = model.get("provider", "unknown")
        # Always return 'google' as provider name for Google models
        # This standardizes frontend provider naming
        response_provider = "google" if model_provider == "google" else model_provider
        formatted_models.append({
            "id": model.get("id", model.get("name", "unknown")),
            "name": model.get("name", model.get("id", "unknown")),
            "provider": response_provider
        })
    
    return {"models": formatted_models}

@router.get("/all")
async def list_all_api_models(user_id: dict = Depends(get_current_user)):
    """Get all API models for authenticated user"""
    # Delegate to list_api_models logic (fetch_models_for_user)
    return await list_api_models(provider=None, user_id=user_id)

@router.post("/refresh")
async def refresh_api_cache(user_id: dict = Depends(get_current_user)):
    """Refresh API model cache for authenticated user"""
    model_registry = get_model_registry()
    
    # Clear ModelRegistry cache for this user
    model_registry.clear_cache(user_id["id"])
    
    # Fetch fresh models (will be cached automatically)
    models = await model_registry.fetch_models_for_user(user_id["id"])
    
    # Return formatted models
    return await list_api_models(provider=None, user_id=user_id)

@router.get("/dynamic")
async def list_dynamic_models(provider: str = Query(None), user_id: dict = Depends(get_current_user)):
    """Get models dynamically from provider APIs using ModelRegistry"""
    print(f"DEBUG: Dynamic models route - Provider: {provider}, User: {user_id['id']}")
    
    if not provider:
        raise HTTPException(400, "Provider parameter is required for dynamic model fetching")
    
    # Map frontend provider names to backend names
    # Accept both 'google' and 'gemini' as input, but always return 'google'
    provider_mapping = {
        'gemini': 'google',  # Accept 'gemini' from frontend, map to 'google' for backend
        'claude': 'anthropic',
        'grok': 'xai'
    }
    
    # Map to backend provider name for ModelRegistry
    backend_provider = provider_mapping.get(provider, provider)
    
    # Use ModelRegistry to fetch models for this provider
    model_registry = get_model_registry()
    
    try:
        # Fetch models for this specific provider
        models = await model_registry.fetch_models_for_provider(backend_provider, user_id["id"])
        
        # Convert to frontend format with standardized provider names
        formatted_models = []
        for model in models:
            # Always return 'google' as provider name for Google models
            # This standardizes frontend provider naming
            response_provider = "google" if backend_provider == "google" else provider
            formatted_models.append({
                "id": model.get("id", "unknown"),
                "name": model.get("name", model.get("id", "unknown")),
                "provider": response_provider
            })
        
        print(f"DEBUG: ModelRegistry returned {len(formatted_models)} models for {provider} (backend: {backend_provider})")
        return {"models": formatted_models}
        
    except ValueError as e:
        # Provider not supported
        print(f"ERROR: Unsupported provider {provider} (backend: {backend_provider}): {e}")
        return {"models": []}
    except Exception as e:
        print(f"ERROR: Failed to fetch dynamic models for {provider} (backend: {backend_provider}): {e}")
        # Return empty list instead of fallback models
        return {"models": []}
