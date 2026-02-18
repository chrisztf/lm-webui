"""
Perplexity Search Provider
Implements web search using Perplexity API (Sonar Online models)
"""

import logging
import aiohttp
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class PerplexityProvider:
    """Perplexity search provider using Sonar Online models"""
    
    def __init__(self):
        self.base_url = "https://api.perplexity.ai/chat/completions"
        
    async def search(self, query: str, max_results: int = 5, api_key: str = None) -> List[Dict[str, Any]]:
        """
        Search using Perplexity API
        """
        if not api_key:
            logger.error("Perplexity search failed: Missing API Key")
            return []
            
        try:
            logger.info(f"Searching Perplexity for: '{query}'")
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "sonar-pro", # Latest online model
                "messages": [
                    {"role": "system", "content": "You are a search engine. Provide a concise answer with citations based on real-time web search."},
                    {"role": "user", "content": query}
                ],
                "temperature": 0.1
            }
            
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.post(self.base_url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Perplexity API Error {response.status}: {error_text}")
                        return []
                        
                    data = await response.json()
                    choices = data.get("choices", [])
                    if not choices:
                        return []
                        
                    content = choices[0]["message"]["content"]
                    citations = data.get("citations", [])
                    
                    # Perplexity returns a synthesized answer. 
                    # We can treat this as a single "result" or try to map citations.
                    # For RAG, the content itself is the best result.
                    
                    results = []
                    
                    # Add the synthesized answer as the primary result
                    results.append({
                        "title": f"Perplexity Answer for: {query}",
                        "url": "https://www.perplexity.ai",
                        "description": content,
                        "content": content, # Already full content
                        "source": "perplexity",
                        "search_engine": "perplexity"
                    })
                    
                    # Add citations as separate results if possible
                    # Perplexity doesn't give snippets for citations in this endpoint usually, just URLs.
                    for i, url in enumerate(citations):
                        results.append({
                            "title": f"Citation {i+1}",
                            "url": url,
                            "description": "Citation source provided by Perplexity.",
                            "source": "perplexity",
                            "search_engine": "perplexity"
                        })
                        
                    return results
            
        except Exception as e:
            logger.error(f"Perplexity search failed: {str(e)}")
            return []
