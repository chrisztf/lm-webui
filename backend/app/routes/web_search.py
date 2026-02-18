"""
Web Search Routes
Handles online web search functionality using the RAG Web Search Engine
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime

from app.security.auth.dependencies import get_current_user
from app.rag.web_search import web_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["web_search"])

# Re-export legacy global variable for backward compatibility if any
web_search_manager = web_engine

@router.post("/web")
async def web_search(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Perform web search
    
    Args:
        request: Contains query and search parameters
    """
    try:
        query = request.get("query", "")
        max_results = request.get("max_results", 10)
        region = request.get("region", "wt-wt")
        provider = request.get("provider", "duckduckgo")
        
        if not query:
            raise HTTPException(400, "Search query is required")
        
        results = await web_engine.search(
            query=query,
            provider=provider,
            max_results=max_results,
            region=region
        )
        
        return {
            "success": True,
            "query": query,
            "results": results,
            "total_results": len(results),
            "search_engine": provider,
            "search_type": "web"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Web search endpoint error: {str(e)}")
        raise HTTPException(500, f"Web search failed: {str(e)}")

@router.post("/web/images")
async def web_image_search(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Perform image search
    """
    try:
        query = request.get("query", "")
        max_results = request.get("max_results", 20)
        region = request.get("region", "wt-wt")
        
        if not query:
            raise HTTPException(400, "Search query is required")
        
        results = await web_engine.ddg.search_images(
            query=query,
            max_results=max_results,
            region=region
        )
        
        return {
            "success": True,
            "query": query,
            "results": results,
            "total_results": len(results),
            "search_engine": "duckduckgo",
            "search_type": "images"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image search endpoint error: {str(e)}")
        raise HTTPException(500, f"Image search failed: {str(e)}")

@router.post("/web/news")
async def web_news_search(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Perform news search
    """
    try:
        query = request.get("query", "")
        max_results = request.get("max_results", 20)
        region = request.get("region", "wt-wt")
        
        if not query:
            raise HTTPException(400, "Search query is required")
        
        results = await web_engine.ddg.search_news(
            query=query,
            max_results=max_results,
            region=region
        )
        
        return {
            "success": True,
            "query": query,
            "results": results,
            "total_results": len(results),
            "search_engine": "duckduckgo",
            "search_type": "news"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"News search endpoint error: {str(e)}")
        raise HTTPException(500, f"News search failed: {str(e)}")

@router.get("/web/engines")
async def get_search_engines(current_user: dict = Depends(get_current_user)):
    """
    Get available search engines and their status
    """
    try:
        engines = [
            {
                "name": "duckduckgo",
                "display_name": "DuckDuckGo",
                "available": True,
                "features": ["web", "images", "news"],
                "privacy_focused": True,
                "api_key_required": False
            }
        ]
        
        return {
            "success": True,
            "engines": engines,
            "default_engine": "duckduckgo"
        }
        
    except Exception as e:
        logger.error(f"Failed to get search engines: {str(e)}")
        raise HTTPException(500, f"Failed to get search engines: {str(e)}")

@router.post("/web/scrape")
async def scrape_web_content(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Scrape content from a specific URL
    """
    try:
        url = request.get("url", "")
        max_length = request.get("max_length", 5000)

        if not url:
            raise HTTPException(400, "URL is required")

        result = await web_engine.scraper.scrape_content(url, max_length)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Web scraping endpoint error: {str(e)}")
        raise HTTPException(500, f"Web scraping failed: {str(e)}")

@router.post("/web/search-and-scrape")
async def search_and_scrape_content(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Search for a query and scrape content from top results
    """
    try:
        query = request.get("query", "")
        max_results = request.get("max_results", 3)
        scrape_length = request.get("content_length", 3000)

        if not query:
            raise HTTPException(400, "Search query is required")

        result = await web_engine.search_and_scrape(
            query=query,
            max_results=max_results,
            scrape_length=scrape_length
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search and scrape endpoint error: {str(e)}")
        raise HTTPException(500, f"Search and scrape failed: {str(e)}")

@router.post("/web/scrape-multiple")
async def scrape_multiple_urls(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Scrape content from multiple URLs concurrently
    """
    try:
        urls = request.get("urls", [])
        max_length = request.get("max_length", 3000)

        if not urls or not isinstance(urls, list):
            raise HTTPException(400, "URLs array is required")

        if len(urls) > 10:
            raise HTTPException(400, "Maximum 10 URLs allowed")

        results = await web_engine.scraper.scrape_multiple_urls(urls, max_length)

        return {
            "success": True,
            "total_urls": len(urls),
            "results": results,
            "successful_scrapes": len([r for r in results if r.get("success")])
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Multiple URL scraping endpoint error: {str(e)}")
        raise HTTPException(500, f"Multiple URL scraping failed: {str(e)}")

@router.get("/web/status")
async def web_search_status():
    """
    Get web search service status
    """
    try:
        # Test DuckDuckGo connectivity with a simple search
        test_results = await web_engine.search(
            query="test",
            max_results=1
        )

        return {
            "status": "healthy",
            "services": {
                "duckduckgo": "available",
                "web_search": "ready",
                "image_search": "ready",
                "news_search": "ready",
                "web_scraping": "ready",
                "content_analysis": "ready"
            },
            "test_query": "successful" if test_results else "no_results"
        }

    except Exception as e:
        logger.error(f"Web search status check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "services": {
                "duckduckgo": "error",
                "web_search": "error",
                "image_search": "error",
                "news_search": "error",
                "web_scraping": "error",
                "content_analysis": "error"
            },
            "error": str(e)
        }

# Model Capabilities Endpoints
@router.get("/models/capabilities")
async def get_model_capabilities(current_user: dict = Depends(get_current_user)):
    """
    Get capabilities for all available models
    """
    try:
        from app.services.model_capabilities import get_reasoning_models
        from app.services.model_registry import get_model_registry

        # Get all available models
        registry = get_model_registry()
        models = await registry.fetch_models_for_user(current_user["id"])
        available_models = [m["id"] for m in models]

        # Filter to reasoning-capable models
        reasoning_models = get_reasoning_models(available_models)

        return {
            "success": True,
            "models": reasoning_models,
            "total_count": len(reasoning_models)
        }

    except Exception as e:
        logger.error(f"Failed to get model capabilities: {str(e)}")
        raise HTTPException(500, f"Failed to get model capabilities: {str(e)}")

@router.post("/models/recommend")
async def recommend_model_for_query(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Recommend the best model for a specific query
    """
    try:
        from app.services.model_capabilities import recommend_model_for_query
        from app.services.model_registry import get_model_registry

        query = request.get("query", "")
        if not query:
            raise HTTPException(400, "Query is required")

        # Get available models and make recommendation
        registry = get_model_registry()
        models = await registry.fetch_models_for_user(current_user["id"])
        available_models = [m["id"] for m in models]
        
        recommendation = recommend_model_for_query(query, available_models)

        if "error" in recommendation:
            raise HTTPException(400, recommendation["error"])

        return {
            "success": True,
            "recommendation": recommendation
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to recommend model: {str(e)}")
        raise HTTPException(500, f"Failed to recommend model: {str(e)}")

@router.get("/models/reasoning-capable")
async def get_reasoning_capable_models(current_user: dict = Depends(get_current_user)):
    """
    Get list of reasoning-capable model names
    """
    try:
        from app.services.model_capabilities import get_reasoning_models
        from app.services.model_registry import get_model_registry

        registry = get_model_registry()
        models = await registry.fetch_models_for_user(current_user["id"])
        available_models = [m["id"] for m in models]
        
        reasoning_models = get_reasoning_models(available_models)

        # Return just the model names for easy filtering
        model_names = [model["name"] for model in reasoning_models]

        return {
            "success": True,
            "models": model_names,
            "count": len(model_names)
        }

    except Exception as e:
        logger.error(f"Failed to get reasoning models: {str(e)}")
        raise HTTPException(500, f"Failed to get reasoning models: {str(e)}")
