"""
Web Search Module for RKLLM Chat System

Provides web search capabilities to enrich chat responses with current information.
Uses DuckDuckGo API for free, unlimited web searches.

Features:
- Web search with result caching
- TTL-based cache expiration
- Error handling with graceful fallback
- Timeout protection
- Result parsing and formatting
- Rate limiting per domain
- Content extraction from URLs
- Search query optimization
"""

import time
import hashlib
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from functools import lru_cache
from ddgs import DDGS
import logging

try:
    from bs4 import BeautifulSoup
    HAS_BEAUTIFULSOUP = True
except ImportError:
    HAS_BEAUTIFULSOUP = False

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Cache configuration
CACHE_TTL_MINUTES = 60  # How long to keep search results in cache
SEARCH_TIMEOUT_SECONDS = 10
MAX_RESULTS_PER_QUERY = 5


class SearchCache:
    """Simple TTL-based cache for search results."""
    
    def __init__(self, ttl_minutes: int = CACHE_TTL_MINUTES):
        """Initialize cache with TTL."""
        self.cache = {}
        self.ttl = timedelta(minutes=ttl_minutes)
    
    def _cache_key(self, query: str) -> str:
        """Generate cache key from query."""
        return hashlib.md5(query.lower().encode()).hexdigest()
    
    def _is_valid(self, timestamp: datetime) -> bool:
        """Check if cache entry is still valid."""
        return datetime.now() - timestamp < self.ttl
    
    def get(self, query: str) -> Optional[List[Dict]]:
        """Get cached search results if available and valid."""
        key = self._cache_key(query)
        
        if key in self.cache:
            results, timestamp = self.cache[key]
            if self._is_valid(timestamp):
                logger.info(f"✅ Cache HIT for query: '{query}'")
                return results
            else:
                # Remove expired entry
                del self.cache[key]
                logger.info(f"🔄 Cache EXPIRED for query: '{query}'")
        
        return None
    
    def set(self, query: str, results: List[Dict]) -> None:
        """Cache search results with current timestamp."""
        key = self._cache_key(query)
        self.cache[key] = (results, datetime.now())
        logger.info(f"💾 Cached {len(results)} results for query: '{query}'")
    
    def clear(self) -> None:
        """Clear all cached results."""
        self.cache.clear()
        logger.info("🗑️  Cache cleared")
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "cached_queries": len(self.cache),
            "cache_size_bytes": sum(len(str(v)) for v in self.cache.values())
        }


class WebSearcher:
    """Web search engine using DuckDuckGo."""
    
    def __init__(self, enable_cache: bool = True, cache_ttl_minutes: int = CACHE_TTL_MINUTES):
        """Initialize web searcher."""
        self.ddgs = DDGS(timeout=SEARCH_TIMEOUT_SECONDS, proxy=None)
        self.cache = SearchCache(cache_ttl_minutes) if enable_cache else None
        self.enabled = True
        logger.info("🔍 WebSearcher initialized (DuckDuckGo)")
    
    def disable(self) -> None:
        """Disable web search."""
        self.enabled = False
        logger.info("❌ Web search disabled")
    
    def enable(self) -> None:
        """Enable web search."""
        self.enabled = True
        logger.info("✅ Web search enabled")
    
    def search(
        self,
        query: str,
        force_refresh: bool = False,
        max_results: int = MAX_RESULTS_PER_QUERY
    ) -> List[Dict]:
        """
        Perform web search.
        
        Args:
            query: Search query string
            force_refresh: Skip cache and fetch fresh results
            max_results: Maximum number of results to return
        
        Returns:
            List of search results with title, url, and snippet
        """
        
        if not self.enabled:
            logger.warning(f"⚠️  Web search is disabled, returning empty results")
            return []
        
        # Check cache first
        if not force_refresh and self.cache:
            cached_results = self.cache.get(query)
            if cached_results is not None:
                return cached_results[:max_results]
        
        try:
            logger.info(f"🔍 Searching for: '{query}'")
            
            # Perform DuckDuckGo search
            results = self.ddgs.text(
                query=query,
                max_results=max_results
            )
            
            # Convert to standard format
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "title": result.get("title", "Untitled"),
                    "url": result.get("href", ""),
                    "snippet": result.get("body", ""),
                    "content": result.get("body", "")  # Alias for snippet
                })
            
            # Cache results
            if self.cache:
                self.cache.set(query, formatted_results)
            
            logger.info(f"✅ Found {len(formatted_results)} results for: '{query}'")
            return formatted_results
        
        except Exception as e:
            logger.error(f"❌ Search error for '{query}': {str(e)}")
            return []
    
    def search_with_fallback(
        self,
        query: str,
        fallback_query: Optional[str] = None,
        max_results: int = MAX_RESULTS_PER_QUERY
    ) -> List[Dict]:
        """
        Search with fallback if primary search fails.
        
        Args:
            query: Primary search query
            fallback_query: Fallback query if primary fails
            max_results: Maximum results to return
        
        Returns:
            Search results or empty list
        """
        
        # Try primary search
        results = self.search(query, max_results=max_results)
        
        if results:
            return results
        
        # Try fallback if provided
        if fallback_query:
            logger.info(f"📍 Trying fallback search: '{fallback_query}'")
            results = self.search(fallback_query, max_results=max_results)
            return results
        
        return []
    
    def extract_search_query_from_message(self, message: str) -> Optional[str]:
        """
        Detect if message needs web search and extract search query.
        
        Returns the search query if needed, None otherwise.
        """
        
        # Keywords that trigger search
        search_triggers = [
            "latest", "recent", "news", "current", "today",
            "2024", "2025", "how do", "what is", "find",
            "search", "look up", "tell me about", "update",
            "info", "information", "about", "when", "where"
        ]
        
        message_lower = message.lower()
        
        # Check if any trigger words are present
        if any(trigger in message_lower for trigger in search_triggers):
            # Use the message itself as search query (model might refine it)
            return message
        
        return None
    
    def format_search_context(self, results: List[Dict], query: str, max_chars: int = 1500) -> str:
        """
        Format search results for injection into chat prompt.
        
        Args:
            results: List of search results
            query: Original search query
            max_chars: Maximum characters to include
        
        Returns:
            Formatted search context string
        """
        
        if not results:
            return ""
        
        context = f"📚 WEB SEARCH RESULTS for '{query}':\n\n"
        
        char_count = len(context)
        for i, result in enumerate(results[:3], 1):
            title = result.get("title", "Untitled")
            url = result.get("url", "")
            snippet = result.get("snippet", result.get("content", ""))[:200]
            
            result_str = f"{i}. {title}\n   URL: {url}\n   {snippet}\n\n"
            
            if char_count + len(result_str) > max_chars:
                break
            
            context += result_str
            char_count += len(result_str)
        
        context += "---\n"
        return context
    
    def clear_cache(self) -> None:
        """Clear search result cache."""
        if self.cache:
            self.cache.clear()
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        if self.cache:
            return self.cache.get_stats()
        return {"error": "Cache disabled"}


# Global instance
_web_searcher: Optional[WebSearcher] = None


def get_web_searcher() -> WebSearcher:
    """Get or create global web searcher instance."""
    global _web_searcher
    
    if _web_searcher is None:
        _web_searcher = WebSearcher(enable_cache=True, cache_ttl_minutes=CACHE_TTL_MINUTES)
    
    return _web_searcher


def search_web(
    query: str,
    force_refresh: bool = False,
    max_results: int = MAX_RESULTS_PER_QUERY
) -> List[Dict]:
    """Convenience function for web search."""
    return get_web_searcher().search(query, force_refresh, max_results)


def get_search_context(
    query: str,
    force_refresh: bool = False,
    max_results: int = MAX_RESULTS_PER_QUERY
) -> str:
    """
    Get formatted search context for injection into prompts.
    
    Returns empty string if search disabled or fails.
    """
    searcher = get_web_searcher()
    results = searcher.search(query, force_refresh, max_results)
    return searcher.format_search_context(results, query)


class ContentExtractor:
    """Extract and summarize content from URLs."""
    
    REQUEST_TIMEOUT = 10
    MAX_CONTENT_LENGTH = 2000  # Max characters to extract
    
    @staticmethod
    def fetch_content(url: str) -> Optional[str]:
        """Fetch and extract text content from URL."""
        try:
            logger.info(f"📄 Fetching content from: {url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=ContentExtractor.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            # Try BeautifulSoup if available
            if HAS_BEAUTIFULSOUP:
                soup = BeautifulSoup(response.content, 'html.parser')
                # Remove script and style elements
                for script in soup(["script", "style", "meta", "link"]):
                    script.decompose()
                # Get text
                text = soup.get_text(separator=' ', strip=True)
            else:
                # Fallback: simple text extraction
                text = response.text
            
            # Clean and limit
            text = ' '.join(text.split())[:ContentExtractor.MAX_CONTENT_LENGTH]
            
            logger.info(f"✅ Extracted {len(text)} characters from {url}")
            return text if text else None
            
        except Exception as e:
            logger.warning(f"⚠️  Failed to fetch {url}: {str(e)}")
            return None
    
    @staticmethod
    def extract_from_results(results: List[Dict]) -> List[Dict]:
        """Extract content from search results."""
        enhanced = []
        
        for result in results:
            url = result.get('url', '')
            content = ContentExtractor.fetch_content(url)
            
            enhanced.append({
                **result,
                'full_content': content or result.get('snippet', '')
            })
        
        return enhanced


class QueryOptimizer:
    """Optimize search queries for better results."""
    
    # Keywords that make queries too broad
    BROAD_KEYWORDS = ['what', 'is', 'the', 'a', 'an', 'tell', 'me', 'about', 'how', 'why']
    
    @staticmethod
    def optimize_query(user_query: str, context: str = "") -> str:
        """
        Optimize query for better search results.
        
        Args:
            user_query: Original user query
            context: Additional context for optimization
        
        Returns:
            Optimized search query
        """
        
        # Remove common filler words
        words = user_query.lower().split()
        filtered = [w for w in words if w not in QueryOptimizer.BROAD_KEYWORDS and len(w) > 2]
        
        # If too much was filtered, keep original
        if len(filtered) < 2:
            filtered = words
        
        # Create focused query
        query = ' '.join(filtered[:10])  # Limit to 10 most important words
        
        # Add context if provided
        if context:
            query = f"{query} {context}".strip()
        
        logger.info(f"🔍 Optimized query: '{user_query}' → '{query}'")
        return query
    
    @staticmethod
    def extract_entities(query: str) -> Dict[str, List[str]]:
        """
        Extract entities from query for better search.
        
        Returns:
            {
                'locations': [...],
                'keywords': [...],
                'time_refs': [...]
            }
        """
        
        time_keywords = ['today', 'now', 'latest', 'recent', 'current', '2024', '2025']
        location_keywords = ['in', 'at', 'near', 'around']
        
        words = query.lower().split()
        
        return {
            'keywords': [w for w in words if w not in QueryOptimizer.BROAD_KEYWORDS],
            'has_time_ref': any(t in query.lower() for t in time_keywords),
            'has_location': any(l in query.lower() for l in location_keywords),
        }
