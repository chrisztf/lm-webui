"""
Bing Search Provider
Implements web search using Bing Web Search API
"""

import logging
import aiohttp
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class BingProvider:
    """Bing search provider"""
    
    def __init__(self):
        self.base_url = "https://api.bing.microsoft.com/v7.0/search"
        
    async def search(self, query: str, max_results: int = 10, api_key: str = None) -> List[Dict[str, Any]]:
        """
        Search using Bing Search API
        """
        if not api_key:
            logger.error("Bing search failed: Missing API Key")
            return []
            
        try:
            logger.info(f"Searching Bing for: '{query}'")
            
            headers = {"Ocp-Apim-Subscription-Key": api_key}
            params = {
                "q": query,
                "count": min(max_results, 50),
                "offset": 0,
                "mkt": "en-US",
                "safesearch": "Moderate"
            }
            
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Bing API Error {response.status}: {error_text}")
                        return []
                        
                    data = await response.json()
                    web_pages = data.get("webPages", {}).get("value", [])
                    
                    results = []
                    for item in web_pages:
                        results.append({
                            "title": item.get("name", ""),
                            "url": item.get("url", ""),
                            "description": item.get("snippet", ""),
                            "source": "bing",
                            "search_engine": "bing"
                        })
                        
                    logger.info(f"Bing found {len(results)} results")
                    return results
            
        except Exception as e:
            logger.error(f"Bing search failed: {str(e)}")
            return []
