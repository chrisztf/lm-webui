"""
Google Programmable Search Engine Provider
Implements web search using Google Custom Search JSON API
"""

import logging
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

class GooglePSEProvider:
    """Google Programmable Search Engine provider"""
    
    def __init__(self):
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        self.headers = {"Content-Type": "application/json"}
        
    async def search(self, query: str, max_results: int = 10, api_key: str = None, cx: str = None) -> List[Dict[str, Any]]:
        """
        Search using Google PSE API
        """
        if not api_key or not cx:
            logger.error("Google PSE search failed: Missing API Key or Search Engine ID (CX)")
            return []
            
        try:
            logger.info(f"Searching Google PSE for: '{query}'")
            
            results = []
            start_index = 1
            results_to_fetch = min(max_results, 30) # Hard cap to avoid excessive quota usage
            
            async with aiohttp.ClientSession(headers=self.headers) as session:
                while len(results) < results_to_fetch:
                    # Google PSE allows max 10 results per page
                    num_results_this_page = min(results_to_fetch - len(results), 10)
                    if num_results_this_page <= 0:
                        break
                        
                    params = {
                        "key": api_key,
                        "cx": cx,
                        "q": query,
                        "num": num_results_this_page,
                        "start": start_index
                    }
                    
                    async with session.get(self.base_url, params=params) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"Google PSE API Error {response.status}: {error_text}")
                            break
                            
                        data = await response.json()
                        items = data.get("items", [])
                        
                        if not items:
                            break
                            
                        for item in items:
                            results.append({
                                "title": item.get("title", ""),
                                "url": item.get("link", ""),
                                "description": item.get("snippet", ""),
                                "source": "google_pse",
                                "search_engine": "google"
                            })
                            
                        start_index += len(items)
                        
                        # Stop if we didn't get a full page (end of results)
                        if len(items) < num_results_this_page:
                            break
            
            logger.info(f"Google PSE found {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Google PSE search failed: {str(e)}")
            return []
