"""
Unified Web Search Engine
Orchestrates search providers and scraping for the RAG pipeline
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime

from .duckduckgo import DuckDuckGoProvider
from .google_pse import GooglePSEProvider
from .perplexity import PerplexityProvider
from .bing import BingProvider
from .scraper import WebScraper
from app.services.model_registry import get_model_registry
from app.security.encryption import decrypt_key

# Lazy import for content analyzer to avoid circular deps
# from app.services.content_analyzer import analyze_web_content

logger = logging.getLogger(__name__)

class WebSearchEngine:
    """
    Unified engine for web search and content retrieval.
    This replaces the legacy WebSearchManager in app/routes/web_search.py
    """
    
    def __init__(self):
        self.ddg = DuckDuckGoProvider()
        self.google = GooglePSEProvider()
        self.perplexity = PerplexityProvider()
        self.bing = BingProvider()
        self.scraper = WebScraper()
        
    async def search(
        self, 
        query: str, 
        provider: str = "duckduckgo", 
        max_results: int = 10,
        region: str = "wt-wt",
        user_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform a web search
        """
        provider = provider.lower()
        
        if user_id:
            try:
                registry = get_model_registry()
                keys = registry.get_user_api_keys(user_id)
                
                if provider == "google":
                    # Fetch keys using frontend provider names
                    api_key = keys.get("google_search")
                    cx = keys.get("google_cx")
                    
                    if api_key and cx:
                        try: api_key = decrypt_key(api_key)
                        except: pass
                        try: cx = decrypt_key(cx)
                        except: pass
                        return await self.google.search(query, max_results, api_key=api_key, cx=cx)
                    else:
                        logger.warning(f"Google Search keys missing for user {user_id}")

                elif provider == "perplexity":
                    api_key = keys.get("perplexity")
                    if api_key:
                        try: api_key = decrypt_key(api_key)
                        except: pass
                        return await self.perplexity.search(query, max_results, api_key=api_key)
                    else:
                        logger.warning(f"Perplexity keys missing for user {user_id}")

                elif provider == "bing":
                    api_key = keys.get("bing_search")
                    if api_key:
                        try: api_key = decrypt_key(api_key)
                        except: pass
                        return await self.bing.search(query, max_results, api_key=api_key)
                    else:
                        logger.warning(f"Bing keys missing for user {user_id}")

            except Exception as e:
                logger.error(f"Error fetching search keys: {e}")
                
        # Default to DuckDuckGo if specific provider fails or is not configured
        if provider != "duckduckgo":
            logger.info(f"Falling back to DuckDuckGo (requested: {provider})")
            
        return await self.ddg.search(query, max_results, region)

    async def search_and_scrape(
        self, 
        query: str, 
        max_results: int = 5,
        scrape_length: int = 3000,
        provider: str = "duckduckgo",
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Search and immediately scrape the top results
        """
        try:
            # 1. Search
            search_results = await self.search(
                query, 
                max_results=max_results, 
                provider=provider, 
                user_id=user_id
            )
            
            if not search_results:
                return {
                    "success": False,
                    "error": "No search results found",
                    "query": query,
                    "results": []
                }
                
            # 2. Scrape top results (limit concurrent scraping to 3 to be fast)
            urls_to_scrape = [
                res["url"] for res in search_results[:3] 
                if res.get("url")
            ]
            
            scraped_data = []
            if urls_to_scrape:
                scraped_data = await self.scraper.scrape_multiple_urls(urls_to_scrape, scrape_length)
                
            # 3. Merge results
            final_results = []
            for i, result in enumerate(search_results):
                # Find matching scrape data
                scrape_info = None
                if i < len(scraped_data):
                     # Simple index matching since we scraped the top N
                     if scraped_data[i].get("url") == result["url"]:
                         scrape_info = scraped_data[i]
                
                if scrape_info and scrape_info.get("success"):
                    result["scraped_content"] = scrape_info.get("content", "")
                    result["scraped_title"] = scrape_info.get("title", "")
                    result["scraped_description"] = scrape_info.get("description", "")
                
                final_results.append(result)
                
            return {
                "success": True,
                "query": query,
                "results": final_results,
                "total_results": len(final_results)
            }
            
        except Exception as e:
            logger.error(f"Search and scrape failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "results": []
            }

# Global instance
web_engine = WebSearchEngine()
