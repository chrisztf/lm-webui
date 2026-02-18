"""
Web Scraper Module
Handles scraping content from URLs with intelligent parsing and cleanup
"""

import logging
import aiohttp
import asyncio
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re

logger = logging.getLogger(__name__)

class WebScraper:
    """Web scraper for extracting content from URLs"""

    def __init__(self):
        self.session_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }
        self.timeout = aiohttp.ClientTimeout(total=15, connect=5)

    async def scrape_content(self, url: str, max_length: int = 5000) -> Dict[str, Any]:
        """
        Scrape content from a URL

        Args:
            url: URL to scrape
            max_length: Maximum content length to extract

        Returns:
            Scraped content with metadata
        """
        try:
            async with aiohttp.ClientSession(headers=self.session_headers, timeout=self.timeout) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}",
                            "url": url
                        }

                    content_type = response.headers.get('content-type', '').lower()
                    if 'text/html' not in content_type:
                        return {
                            "success": False,
                            "error": "Not HTML content",
                            "content_type": content_type,
                            "url": url
                        }

                    html = await response.text()
                    return self._process_html(html, url, max_length)

        except Exception as e:
            logger.error(f"Scraping failed for {url}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "url": url
            }

    def _process_html(self, html: str, url: str, max_length: int) -> Dict[str, Any]:
        """Process HTML content"""
        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Extract title
            title = soup.title.string if soup.title else ""
            title = title.strip() if title else ""

            # Extract meta description
            try:
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                description = meta_desc['content'] if meta_desc else ""
            except Exception as e:
                logger.warning(f"Error extracting description: {e}")
                description = ""

            # Extract main content
            content = self._extract_main_content(soup)

            # Truncate if too long
            if len(content) > max_length:
                content = content[:max_length] + "..."

            # Extract domain
            domain = urlparse(url).netloc

            return {
                "success": True,
                "url": url,
                "domain": domain,
                "title": title,
                "description": description,
                "content": content,
                "content_length": len(content),
                "scraped_at": asyncio.get_event_loop().time()
            }
        except Exception as e:
            logger.error(f"HTML processing failed: {str(e)}")
            return {
                "success": False,
                "error": f"Processing error: {str(e)}",
                "url": url
            }

    def _extract_main_content(self, soup) -> str:
        """Extract main content from HTML soup"""
        # 1. Remove obvious noise
        self._remove_noise(soup)

        # 2. Try specific semantic selectors first
        content_selectors = [
            'article',
            'main',
            '[role="main"]',
            '.content',
            '.post-content',
            '.entry-content',
            '.article-content',
            '.main-content',
            '#content',
            '#main',
            '.post',
            '.article'
        ]

        best_content = ""
        best_length = 0

        # Check explicit selectors
        for selector in content_selectors:
            elements = soup.select(selector)
            for el in elements:
                # Get text with structural preservation
                text = self._get_structured_text(el)
                if len(text) > best_length:
                    best_length = len(text)
                    best_content = text
        
        # If we found something substantial, return it
        if best_length > 500:
            return self._clean_text(best_content)

        # 3. Fallback: Text Density Heuristic
        # Find the block-level element with the most text
        body = soup.body
        if not body:
            return ""
            
        max_text_len = 0
        max_elem = None
        
        # Iterate over common block elements
        for tag in ['div', 'section', 'td']:
            for elem in body.find_all(tag, recursive=True):
                # Don't go too deep if we already have a parent
                # (Simple heuristic: direct text length)
                text_len = len(elem.get_text(strip=True))
                if text_len > max_text_len:
                    # Check link density - if it's mostly links, it's likely a menu/list
                    links_len = len(''.join([a.get_text(strip=True) for a in elem.find_all('a')]))
                    if links_len / (text_len + 1) < 0.5: # Less than 50% links
                        max_text_len = text_len
                        max_elem = elem
        
        if max_elem:
             return self._clean_text(self._get_structured_text(max_elem))
             
        # 4. Last resort: Body text
        return self._clean_text(self._get_structured_text(body))

    def _remove_noise(self, soup):
        """Remove noisy elements from soup"""
        try:
            # Tags to remove
            noise_tags = [
                'script', 'style', 'nav', 'header', 'footer', 'aside', 
                'noscript', 'iframe', 'svg', 'form', 'button', 'input', 
                'select', 'textarea', 'meta', 'link'
            ]
            
            # Classes/IDs to remove (regex)
            noise_patterns = re.compile(
                r'menu|sidebar|comment|ad-|advert|banner|cookie|share|social|login|signup|widget|related|recommended|footer|header|nav|navigation', 
                re.I
            )
            
            for element in soup(noise_tags):
                if element:
                    element.decompose()
                
            # Remove elements with noisy classes/ids
            # Note: This is aggressive, might remove content if class name is ambiguous
            for tag in ['div', 'section', 'ul', 'ol', 'aside']:
                for elem in soup.find_all(tag):
                    if not elem: continue
                    
                    # Safe get for class
                    try:
                        cls_list = elem.get('class')
                        if cls_list:
                            cls = ' '.join(cls_list)
                        else:
                            cls = ''
                            
                        # Safe get for id
                        id_ = elem.get('id')
                        if not id_: id_ = ''
                        
                        if noise_patterns.search(cls) or noise_patterns.search(id_):
                            elem.decompose()
                    except AttributeError:
                        continue
        except Exception as e:
            logger.error(f"Error in _remove_noise: {e}")
            # Continue anyway

    def _get_structured_text(self, elem) -> str:
        """Get text with proper separation for block elements"""
        # Replace breaks with newline
        for br in elem.find_all("br"):
            br.replace_with("\n")
            
        # Add newlines around block elements to prevent merging
        # This is a bit of a hack but works well for BeautifulSoup
        text = elem.get_text(separator='\n\n', strip=True)
        return text

    def _clean_text(self, text: str) -> str:
        """Clean up text content"""
        # Collapse multiple newlines
        text = re.sub(r'\n\s*\n', '\n\n', text)
        # Collapse multiple spaces
        text = re.sub(r'[ \t]+', ' ', text)
        return text.strip()

    async def scrape_multiple_urls(self, urls: List[str], max_length: int = 3000) -> List[Dict[str, Any]]:
        """
        Scrape multiple URLs concurrently

        Args:
            urls: List of URLs to scrape
            max_length: Maximum content length per URL

        Returns:
            List of scraped content results
        """
        semaphore = asyncio.Semaphore(5)  # Limit concurrent requests

        async def scrape_with_semaphore(url: str):
            async with semaphore:
                return await self.scrape_content(url, max_length)

        # Filter out empty or invalid URLs
        valid_urls = [url for url in urls if url and url.startswith(('http://', 'https://'))]
        
        if not valid_urls:
            return []

        tasks = [scrape_with_semaphore(url) for url in valid_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "success": False,
                    "error": str(result),
                    "url": valid_urls[i]
                })
            else:
                processed_results.append(result)

        return processed_results
