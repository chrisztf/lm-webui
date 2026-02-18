"""
Content Analyzer Service
Analyzes scraped web content and extracts insights for reasoning
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ContentAnalyzer:
    """Analyzes web content for relevance and insights"""

    def __init__(self):
        self.min_content_length = 100
        self.max_summary_length = 500

    async def analyze_content(self, content: str, query: str = "") -> Dict[str, Any]:
        """
        Analyze web content for relevance and extract key insights

        Args:
            content: Scraped web content
            query: Original search query for relevance scoring

        Returns:
            Analysis results with insights, relevance score, and summary
        """
        try:
            if not content or len(content.strip()) < self.min_content_length:
                return {
                    "success": False,
                    "error": "Content too short or empty",
                    "relevance_score": 0,
                    "insights": [],
                    "summary": ""
                }

            # Extract key insights
            insights = self._extract_insights(content)

            # Calculate relevance score
            relevance_score = self._calculate_relevance(content, query)

            # Generate summary
            summary = self._generate_summary(content)

            # Extract key facts and data points
            facts = self._extract_facts(content)

            # Identify content type and quality
            content_type = self._classify_content_type(content)
            quality_score = self._assess_content_quality(content)

            return {
                "success": True,
                "relevance_score": relevance_score,
                "insights": insights,
                "summary": summary,
                "facts": facts,
                "content_type": content_type,
                "quality_score": quality_score,
                "word_count": len(content.split()),
                "analyzed_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Content analysis failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "relevance_score": 0,
                "insights": [],
                "summary": ""
            }

    def _extract_insights(self, content: str) -> List[str]:
        """Extract key insights from content"""
        insights = []

        # Look for numbered or bulleted lists
        list_patterns = [
            r'\d+\.\s*([^\n]+)',  # Numbered lists
            r'•\s*([^\n]+)',      # Bullet points
            r'-\s*([^\n]+)',       # Dash lists
            r'\*\s*([^\n]+)',      # Asterisk lists
        ]

        for pattern in list_patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            insights.extend(matches[:5])  # Limit to top 5 insights

        # Look for key phrases indicating important information
        key_phrases = [
            r'importantly[^.]*\.',
            r'significantly[^.]*\.',
            r'notably[^.]*\.',
            r'crucially[^.]*\.',
            r'essentially[^.]*\.',
            r'key[^.]*\.',
            r'main[^.]*\.',
            r'primary[^.]*\.',
        ]

        for pattern in key_phrases:
            matches = re.findall(pattern, content, re.IGNORECASE)
            insights.extend(matches[:3])

        # Remove duplicates and clean up
        insights = list(set(insights))
        insights = [insight.strip() for insight in insights if len(insight.strip()) > 10]

        return insights[:10]  # Limit to top 10 insights

    def _calculate_relevance(self, content: str, query: str) -> float:
        """Calculate relevance score based on query matching"""
        if not query:
            return 0.5  # Neutral score if no query provided

        content_lower = content.lower()
        query_lower = query.lower()

        # Exact query matches
        exact_matches = len(re.findall(re.escape(query_lower), content_lower))

        # Partial word matches
        query_words = query_lower.split()
        word_matches = sum(1 for word in query_words if word in content_lower)

        # Calculate score (0-1 scale)
        exact_score = min(exact_matches * 0.3, 0.5)  # Max 0.5 for exact matches
        word_score = min(word_matches * 0.1, 0.4)   # Max 0.4 for word matches

        total_score = exact_score + word_score

        # Boost score for content that seems comprehensive
        if len(content.split()) > 500:
            total_score += 0.1

        return min(total_score, 1.0)

    def _generate_summary(self, content: str) -> str:
        """Generate a concise summary of the content"""
        # Simple extractive summarization - take first few sentences
        sentences = re.split(r'[.!?]+', content)

        # Filter out very short sentences and clean up
        valid_sentences = [
            s.strip() for s in sentences
            if len(s.strip()) > 20 and not s.strip().startswith(('http', 'www.'))
        ]

        # Take first 2-3 sentences for summary
        summary_sentences = valid_sentences[:3]

        summary = '. '.join(summary_sentences)
        if not summary.endswith('.'):
            summary += '.'

        # Truncate if too long
        if len(summary) > self.max_summary_length:
            summary = summary[:self.max_summary_length] + '...'

        return summary

    def _extract_facts(self, content: str) -> List[str]:
        """Extract factual statements from content"""
        facts = []

        # Look for sentences with numbers, dates, or specific facts
        fact_patterns = [
            r'\b\d{4}\b',  # Years
            r'\b\d{1,2}/\d{1,2}/\d{4}\b',  # Dates
            r'\b\d+(\.\d+)?%\b',  # Percentages
            r'\$\d+(\.\d+)?',  # Dollar amounts
            r'\b\d+(\.\d+)?\s*(million|billion|trillion)\b',  # Large numbers
        ]

        sentences = re.split(r'[.!?]+', content)

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:
                continue

            # Check if sentence contains factual indicators
            has_fact = any(re.search(pattern, sentence) for pattern in fact_patterns)

            if has_fact:
                facts.append(sentence)

        return facts[:5]  # Limit to top 5 facts

    def _classify_content_type(self, content: str) -> str:
        """Classify the type of content"""
        content_lower = content.lower()

        # Check for different content types
        if any(keyword in content_lower for keyword in ['research', 'study', 'paper', 'journal']):
            return 'academic_research'
        elif any(keyword in content_lower for keyword in ['news', 'breaking', 'reported', 'announced']):
            return 'news_article'
        elif any(keyword in content_lower for keyword in ['tutorial', 'guide', 'how to', 'step by step']):
            return 'tutorial_guide'
        elif any(keyword in content_lower for keyword in ['review', 'rating', 'recommend']):
            return 'review_rating'
        elif any(keyword in content_lower for keyword in ['definition', 'meaning', 'what is']):
            return 'definition_explanation'
        elif any(keyword in content_lower for keyword in ['data', 'statistics', 'chart', 'graph']):
            return 'data_statistics'
        else:
            return 'general_information'

    def _assess_content_quality(self, content: str) -> float:
        """Assess content quality on a 0-1 scale"""
        score = 0.5  # Base score

        # Length bonus
        word_count = len(content.split())
        if word_count > 1000:
            score += 0.2
        elif word_count > 500:
            score += 0.1
        elif word_count < 100:
            score -= 0.2

        # Structure bonus (has headings, lists, etc.)
        if re.search(r'\n#{1,6}\s', content):  # Markdown headings
            score += 0.1
        if re.search(r'\n\d+\.\s', content):  # Numbered lists
            score += 0.1
        if re.search(r'\n[-\*]\s', content):  # Bullet lists
            score += 0.1

        # Citation bonus (has references, links, etc.)
        if re.search(r'\[.*?\]\(.*?\)', content):  # Markdown links
            score += 0.1
        if re.search(r'https?://', content):  # URLs
            score += 0.05

        # Language quality (avoid excessive caps, etc.)
        caps_ratio = sum(1 for c in content if c.isupper()) / len(content) if content else 0
        if caps_ratio > 0.3:  # Too many caps
            score -= 0.2

        return max(0.0, min(1.0, score))

    async def compare_sources(self, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compare multiple sources for consistency and reliability

        Args:
            sources: List of analyzed content sources

        Returns:
            Comparison analysis
        """
        if len(sources) < 2:
            return {"error": "Need at least 2 sources to compare"}

        # Extract key facts from each source
        source_facts = {}
        for i, source in enumerate(sources):
            facts = source.get('facts', [])
            source_facts[f' source_{i+1}'] = facts

        # Calculate consistency score
        consistency_score = self._calculate_consistency(source_facts)

        # Identify unique insights per source
        unique_insights = {}
        all_insights = []

        for i, source in enumerate(sources):
            source_insights = source.get('insights', [])
            unique_insights[f'source_{i+1}'] = source_insights
            all_insights.extend(source_insights)

        # Find common themes
        common_themes = self._find_common_themes(all_insights)

        return {
            "consistency_score": consistency_score,
            "unique_insights": unique_insights,
            "common_themes": common_themes,
            "source_count": len(sources),
            "recommendation": self._generate_comparison_recommendation(consistency_score, len(sources))
        }

    def _calculate_consistency(self, source_facts: Dict[str, List[str]]) -> float:
        """Calculate consistency score between sources"""
        if len(source_facts) < 2:
            return 1.0

        # Simple consistency check - count overlapping facts
        all_facts = []
        for facts in source_facts.values():
            all_facts.extend(facts)

        # Count unique facts
        unique_facts = set()
        for fact in all_facts:
            # Normalize fact for comparison
            normalized = fact.lower().strip()
            unique_facts.add(normalized)

        # Calculate overlap ratio
        total_facts = len(all_facts)
        unique_count = len(unique_facts)

        if total_facts == 0:
            return 1.0

        # Higher overlap = higher consistency
        overlap_ratio = 1 - (unique_count / total_facts)
        return min(1.0, overlap_ratio + 0.5)  # Boost baseline consistency

    def _find_common_themes(self, insights: List[str]) -> List[str]:
        """Find common themes across insights"""
        if len(insights) < 3:
            return []

        # Simple keyword-based theme extraction
        themes = []
        theme_keywords = {
            'technology': ['tech', 'software', 'ai', 'machine learning', 'algorithm'],
            'science': ['research', 'study', 'experiment', 'data', 'analysis'],
            'business': ['company', 'market', 'revenue', 'growth', 'strategy'],
            'health': ['medical', 'treatment', 'disease', 'health', 'clinical'],
        }

        for theme, keywords in theme_keywords.items():
            theme_insights = []
            for insight in insights:
                insight_lower = insight.lower()
                if any(keyword in insight_lower for keyword in keywords):
                    theme_insights.append(insight)

            if len(theme_insights) >= 2:  # At least 2 insights mention this theme
                themes.append({
                    'theme': theme,
                    'count': len(theme_insights),
                    'insights': theme_insights[:3]  # Top 3 insights
                })

        return themes

    def _generate_comparison_recommendation(self, consistency_score: float, source_count: int) -> str:
        """Generate recommendation based on source comparison"""
        if consistency_score > 0.8:
            return "High consistency across sources - information appears reliable"
        elif consistency_score > 0.6:
            return "Moderate consistency - verify key facts with additional sources"
        elif consistency_score > 0.4:
            return "Low consistency - cross-reference information carefully"
        else:
            return "Very low consistency - seek additional reliable sources"


# Global instance
content_analyzer = ContentAnalyzer()


# Convenience functions
async def analyze_web_content(content: str, query: str = "") -> Dict[str, Any]:
    """Analyze web content for insights and relevance"""
    return await content_analyzer.analyze_content(content, query)


async def compare_web_sources(sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compare multiple web sources for consistency"""
    return await content_analyzer.compare_sources(sources)
