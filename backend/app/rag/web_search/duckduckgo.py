"""
DuckDuckGo Search Provider
Implements web search using duckduckgo_search library with robustness improvements
"""

import logging
import asyncio
import aiohttp
import time
import random
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from ddgs import DDGS
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

# Global cache to prevent retry loops
# Key: query string, Value: (timestamp, results)
SEARCH_CACHE = {}
# Set of queries currently being searched to prevent concurrent duplicates
PENDING_SEARCHES = set()
CACHE_TTL = 60  # 60 seconds TTL for identical queries

class DuckDuckGoProvider:
    """DuckDuckGo search provider"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://duckduckgo.com/'
        }
        
    async def search(self, query: str, max_results: int = 10, region: str = "wt-wt") -> List[Dict[str, Any]]:
        """
        Search using DuckDuckGo with robust timeout and minimal configuration
        """
        try:
            # Check cache first
            current_time = time.time()
            if query in SEARCH_CACHE:
                timestamp, cached_results = SEARCH_CACHE[query]
                if current_time - timestamp < CACHE_TTL:
                    logger.info(f"Using cached search results for: '{query}'")
                    return cached_results

            # Clean query: Remove common command words that might confuse search engine
            clean_query = query.lower()
            for word in ["search", "find", "look up", "google", "tell me about", "how about", "then", "sesrch again"]:
                clean_query = clean_query.replace(word, "")
            
            clean_query = clean_query.strip()
            if not clean_query:
                clean_query = query.strip()

            # Check if this query is already being searched
            if clean_query in PENDING_SEARCHES:
                logger.info(f"Search already in progress for: '{clean_query}', waiting...")
                # Wait briefly for the other search to potentially finish and populate cache
                for _ in range(10): # Wait up to 5 seconds
                    await asyncio.sleep(0.5)
                    if clean_query in SEARCH_CACHE:
                        timestamp, cached_results = SEARCH_CACHE[clean_query]
                        if current_time - timestamp < CACHE_TTL:
                            logger.info(f"Using cached search results after wait for: '{clean_query}'")
                            return cached_results
                    # If pending flag is gone but no cache (failed?), break and retry
                    if clean_query not in PENDING_SEARCHES:
                        break
            
            # Mark as pending
            PENDING_SEARCHES.add(clean_query)
                
            logger.info(f"Searching DuckDuckGo for: '{clean_query}' (original: '{query}')")
            
            # Run in executor to avoid blocking event loop
            loop = asyncio.get_running_loop()
            results = []
            
            # Simplified DDG search function with explicit cleanup and delay
            def perform_search():
                # Random small delay to avoid rate limiting on rapid follow-ups
                time.sleep(random.uniform(0.5, 1.5))
                
                try:
                    with DDGS(timeout=5) as ddgs:
                        # Use default arguments - let the library handle backend selection internally
                        # Do NOT pass 'backend' parameter to avoid KeyError
                        # Strictly limit max_results to avoid long fetching times
                        return list(ddgs.text(
                            clean_query,
                            max_results=min(max_results, 5), # Cap at 5 for speed/safety
                            region=region,
                            safesearch="moderate"
                        ))
                except Exception as e:
                    logger.warning(f"DDG internal error: {e}")
                    return []

            # Execute with strict timeout to prevent OOM loops
            try:
                # Use a slightly longer timeout for the wrapper, but the internal timeout is 5s
                results = await asyncio.wait_for(
                    loop.run_in_executor(None, perform_search),
                    timeout=8.0 
                )
            except asyncio.TimeoutError:
                logger.warning(f"DDG search timed out after 8s for query: {clean_query}")
                results = []
            except Exception as e:
                logger.warning(f"DDG library search failed: {e}")
                results = []

            # Manual fallback if library fails or times out
            if not results:
                logger.warning("DDG library failed or timed out. Attempting manual fallback...")
                results = await self._manual_search_fallback(clean_query, max_results)
            
            processed_results = []
            for result in results:
                # Normalize result structure
                title = result.get("title", "")
                url = result.get("href") or result.get("url") or result.get("link", "")
                
                if title and url:
                    processed_results.append({
                        "title": title,
                        "url": url,
                        "description": result.get("body", "") or result.get("description", ""),
                        "source": "duckduckgo",
                        "search_engine": "duckduckgo"
                    })
            
            logger.info(f"DuckDuckGo found {len(processed_results)} results")
            
            # Cache the results
            if processed_results:
                SEARCH_CACHE[query] = (time.time(), processed_results)
                # Also cache cleaned query to hit pending waiters
                if clean_query != query:
                    SEARCH_CACHE[clean_query] = (time.time(), processed_results)
                
            return processed_results
            
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {str(e)}")
            return []
        finally:
            # Always remove from pending set
            if 'clean_query' in locals() and clean_query in PENDING_SEARCHES:
                PENDING_SEARCHES.remove(clean_query)
            
    async def _manual_search_fallback(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Manual scraping of DuckDuckGo HTML version"""
        results = []
        try:
            # Use the HTML version which is easier to scrape
            url = "https://html.duckduckgo.com/html/"
            
            async with aiohttp.ClientSession(headers=self.headers) as session:
                # DDG HTML version often requires a POST for the initial search to avoid some bot detection
                async with session.post(url, data={'q': query}, timeout=10) as response:
                    if response.status != 200:
                        logger.error(f"Manual fallback HTTP {response.status}")
                        # Try GET as a last resort
                        async with session.get(f"{url}?q={quote_plus(query)}", timeout=10) as get_response:
                            if get_response.status != 200:
                                return []
                            html = await get_response.text()
                    else:
                        html = await response.text()
                    
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Select result containers
                    # The class names in the HTML version are fairly stable
                    result_containers = soup.select('.result.results_links.results_links_deep.web-result')
                    
                    if not result_containers:
                        # Fallback to broader selector if specific one fails
                        result_containers = soup.select('.links_main.links_deep')

                    for i, container in enumerate(result_containers):
                        if len(results) >= max_results:
                            break
                            
                        title_tag = container.select_one('.result__a')
                        snippet_tag = container.select_one('.result__snippet')
                        
                        if not title_tag:
                            continue
                            
                        title = title_tag.get_text(strip=True)
                        href = title_tag.get('href', '')
                        
                        # Clean up URL
                        if href.startswith('//'):
                            href = 'https:' + href
                        
                        # Handle DDG internal redirect links
                        if 'duckduckgo.com/l/?' in href:
                            import urllib.parse
                            parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                            if 'uddg' in parsed:
                                href = parsed['uddg'][0]
                        
                        description = ""
                        if snippet_tag:
                            description = snippet_tag.get_text(strip=True)
                            
                        if title and href:
                            results.append({
                                "title": title,
                                "url": href,
                                "body": description
                            })
                            
            if not results:
                logger.warning(f"Manual fallback found 0 results for query: {query}")
                            
        except Exception as e:
            logger.error(f"Manual fallback failed: {e}")
            
        return results

    async def search_images(self, query: str, max_results: int = 20, region: str = "wt-wt") -> List[Dict[str, Any]]:
        """Search for images"""
        try:
            loop = asyncio.get_running_loop()
            
            def perform_image_search():
                with DDGS() as ddgs:
                    return list(ddgs.images(
                        keywords=query,
                        max_results=max_results,
                        region=region,
                        safesearch="moderate"
                    ))

            results = await loop.run_in_executor(None, perform_image_search)
            
            processed_results = []
            for result in results:
                processed_results.append({
                    "title": result.get("title", ""),
                    "url": result.get("image", ""),
                    "thumbnail": result.get("thumbnail", ""),
                    "source": result.get("source", ""),
                    "search_engine": "duckduckgo",
                    "type": "image"
                })
                
            return processed_results
        except Exception as e:
            logger.error(f"DDG image search failed: {e}")
            return []

    async def search_news(self, query: str, max_results: int = 20, region: str = "wt-wt") -> List[Dict[str, Any]]:
        """Search for news"""
        try:
            loop = asyncio.get_running_loop()
            
            def perform_news_search():
                with DDGS() as ddgs:
                    return list(ddgs.news(
                        keywords=query,
                        max_results=max_results,
                        region=region,
                        safesearch="moderate"
                    ))

            results = await loop.run_in_executor(None, perform_news_search)
            
            processed_results = []
            for result in results:
                processed_results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "description": result.get("body", ""),
                    "date": result.get("date", ""),
                    "source": result.get("source", ""),
                    "search_engine": "duckduckgo",
                    "type": "news"
                })
                
            return processed_results
        except Exception as e:
            logger.error(f"DDG news search failed: {e}")
            return []
