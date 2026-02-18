"""
Model Capabilities Service
Manages reasoning capabilities and optimal parameters for different LLM models
"""

from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ReasoningStrength(Enum):
    """Reasoning capability levels"""
    BASIC = "basic"
    ADVANCED = "advanced"
    EXPERT = "expert"


class ModelCapabilities:
    """Comprehensive model capabilities database"""

    def __init__(self):
        # Core reasoning capabilities by provider and model
        self.capabilities = self._load_capabilities()

        # Dynamic parameter adjustment rules
        self.parameter_rules = self._load_parameter_rules()

    def _load_capabilities(self) -> Dict[str, Dict[str, Any]]:
        """Load comprehensive model capabilities database"""
        return {
            # OpenAI Models
            "gpt-4o": {
                "supports_reasoning": True,
                "reasoning_strength": ReasoningStrength.EXPERT,
                "max_reasoning_tokens": 8192,
                "optimal_temperature": 0.3,
                "supports_structured_output": True,
                "reasoning_capabilities": [
                    "multi_step_reasoning", "web_search", "code_execution",
                    "mathematical_reasoning", "causal_analysis", "hypothesis_testing"
                ],
                "recommended_for": [
                    "complex_analysis", "research_questions", "technical_problems",
                    "strategic_planning", "scientific_inquiry"
                ],
                "limitations": ["high_cost", "rate_limits"],
                "context_window": 128000
            },
            "gpt-4o-mini": {
                "supports_reasoning": True,
                "reasoning_strength": ReasoningStrength.ADVANCED,
                "max_reasoning_tokens": 4096,
                "optimal_temperature": 0.4,
                "supports_structured_output": True,
                "reasoning_capabilities": [
                    "step_by_step_reasoning", "web_search", "basic_math",
                    "logical_analysis", "problem_solving"
                ],
                "recommended_for": [
                    "analytical_questions", "explanations", "comparisons",
                    "decision_making", "educational_content"
                ],
                "limitations": ["smaller_context", "less_depth"],
                "context_window": 128000
            },
            "gpt-4-turbo": {
                "supports_reasoning": True,
                "reasoning_strength": ReasoningStrength.EXPERT,
                "max_reasoning_tokens": 8192,
                "optimal_temperature": 0.2,
                "supports_structured_output": True,
                "reasoning_capabilities": [
                    "deep_analysis", "creative_reasoning", "ethical_reasoning",
                    "complex_problem_solving", "multi_domain_expertise"
                ],
                "recommended_for": [
                    "philosophical_questions", "ethical_dilemmas", "creative_solutions",
                    "interdisciplinary_problems", "long_form_analysis"
                ],
                "limitations": ["very_high_cost", "slower_responses"],
                "context_window": 128000
            },

            # Anthropic Claude Models
            "claude-3-5-sonnet-20241022": {
                "supports_reasoning": True,
                "reasoning_strength": ReasoningStrength.EXPERT,
                "max_reasoning_tokens": 8192,
                "optimal_temperature": 0.3,
                "supports_structured_output": True,
                "reasoning_capabilities": [
                    "constitutional_reasoning", "safety_analysis", "long_context_reasoning",
                    "nuanced_understanding", "helpful_assistance", "truth_seeking"
                ],
                "recommended_for": [
                    "safety_critical_questions", "ethical_analysis", "long_documents",
                    "nuanced_social_issues", "comprehensive_research"
                ],
                "limitations": ["slower_responses", "higher_cost"],
                "context_window": 200000
            },
            "claude-3-haiku": {
                "supports_reasoning": True,
                "reasoning_strength": ReasoningStrength.ADVANCED,
                "max_reasoning_tokens": 4096,
                "optimal_temperature": 0.5,
                "supports_structured_output": False,
                "reasoning_capabilities": [
                    "fast_reasoning", "basic_analysis", "conversational_reasoning",
                    "quick_problem_solving", "efficient_responses"
                ],
                "recommended_for": [
                    "quick_analysis", "conversational_ai", "basic_questions",
                    "efficient_workflows", "real_time_assistance"
                ],
                "limitations": ["less_depth", "shorter_context"],
                "context_window": 200000
            },

            # Google Gemini Models
            "gemini-2.0-flash-exp": {
                "supports_reasoning": True,
                "reasoning_strength": ReasoningStrength.EXPERT,
                "max_reasoning_tokens": 8192,
                "optimal_temperature": 0.4,
                "supports_structured_output": True,
                "reasoning_capabilities": [
                    "multimodal_reasoning", "real_time_knowledge", "fast_inference",
                    "creative_reasoning", "code_generation", "data_analysis"
                ],
                "recommended_for": [
                    "multimodal_tasks", "current_events", "creative_projects",
                    "code_assistance", "data_science", "real_time_queries"
                ],
                "limitations": ["experimental", "variable_performance"],
                "context_window": 1000000
            },
            "gemini-1.5-pro": {
                "supports_reasoning": True,
                "reasoning_strength": ReasoningStrength.ADVANCED,
                "max_reasoning_tokens": 6144,
                "optimal_temperature": 0.3,
                "supports_structured_output": True,
                "reasoning_capabilities": [
                    "long_context_reasoning", "multimodal_analysis", "comprehensive_understanding",
                    "creative_synthesis", "detailed_explanations"
                ],
                "recommended_for": [
                    "long_documents", "multimodal_analysis", "comprehensive_tasks",
                    "creative_writing", "detailed_explanations", "research_synthesis"
                ],
                "limitations": ["slower_inference", "higher_cost"],
                "context_window": 1000000
            },

            # xAI Grok Models
            "grok-beta": {
                "supports_reasoning": True,
                "reasoning_strength": ReasoningStrength.EXPERT,
                "max_reasoning_tokens": 8192,
                "optimal_temperature": 0.6,
                "supports_structured_output": True,
                "reasoning_capabilities": [
                    "humorous_reasoning", "xai_knowledge", "real_time_web_access",
                    "creative_problem_solving", "honest_assessment", "maximally_helpful"
                ],
                "recommended_for": [
                    "creative_questions", "current_events", "humorous_interactions",
                    "honest_opinions", "real_time_information", "unique_perspectives"
                ],
                "limitations": ["experimental", "variable_tone"],
                "context_window": 128000
            },

            # DeepSeek Models
            "deepseek-chat": {
                "supports_reasoning": True,
                "reasoning_strength": ReasoningStrength.ADVANCED,
                "max_reasoning_tokens": 4096,
                "optimal_temperature": 0.3,
                "supports_structured_output": False,
                "reasoning_capabilities": [
                    "code_reasoning", "mathematical_analysis", "logical_deduction",
                    "programming_assistance", "technical_explanations"
                ],
                "recommended_for": [
                    "coding_questions", "math_problems", "technical_analysis",
                    "programming_help", "algorithm_explanations"
                ],
                "limitations": ["limited_general_reasoning", "shorter_context"],
                "context_window": 32768
            },

            # Meta Llama Models (via various providers)
            "llama-3.1-405b-instruct": {
                "supports_reasoning": True,
                "reasoning_strength": ReasoningStrength.EXPERT,
                "max_reasoning_tokens": 8192,
                "optimal_temperature": 0.3,
                "supports_structured_output": False,
                "reasoning_capabilities": [
                    "long_context_reasoning", "comprehensive_analysis", "instruction_following",
                    "detailed_responses", "knowledge_integration"
                ],
                "recommended_for": [
                    "long_form_content", "comprehensive_analysis", "instructional_tasks",
                    "detailed_responses", "knowledge_synthesis"
                ],
                "limitations": ["slower_responses", "higher_resource_usage"],
                "context_window": 128000
            },
            "llama-3.1-70b-instruct": {
                "supports_reasoning": True,
                "reasoning_strength": ReasoningStrength.ADVANCED,
                "max_reasoning_tokens": 6144,
                "optimal_temperature": 0.4,
                "supports_structured_output": False,
                "reasoning_capabilities": [
                    "balanced_reasoning", "instruction_following", "conversational_ai",
                    "general_assistance", "balanced_responses"
                ],
                "recommended_for": [
                    "general_questions", "conversational_ai", "balanced_analysis",
                    "instructional_content", "versatile_assistance"
                ],
                "limitations": ["moderate_performance", "average_context"],
                "context_window": 128000
            }
        }

    def _load_parameter_rules(self) -> Dict[str, Any]:
        """Load dynamic parameter adjustment rules"""
        return {
            "query_complexity": {
                "simple": {"temperature": 0.7, "max_tokens": 2048},
                "moderate": {"temperature": 0.5, "max_tokens": 4096},
                "complex": {"temperature": 0.3, "max_tokens": 8192},
                "expert": {"temperature": 0.1, "max_tokens": 16384}
            },
            "reasoning_type": {
                "analytical": {"temperature": 0.2, "prioritize": "precision"},
                "creative": {"temperature": 0.7, "prioritize": "diversity"},
                "factual": {"temperature": 0.1, "prioritize": "accuracy"},
                "exploratory": {"temperature": 0.5, "prioritize": "breadth"}
            },
            "content_length": {
                "short": {"max_tokens": 2048},
                "medium": {"max_tokens": 4096},
                "long": {"max_tokens": 8192},
                "extended": {"max_tokens": 16384}
            }
        }

    def get_model_capabilities(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get capabilities for a specific model"""
        # Try exact match first
        if model_name in self.capabilities:
            return self.capabilities[model_name]

        # Try partial matches (for version variations)
        for model_key, capabilities in self.capabilities.items():
            if model_key in model_name or model_name in model_key:
                return capabilities

        return None

    def is_reasoning_capable(self, model_name: str) -> bool:
        """Check if a model supports reasoning"""
        capabilities = self.get_model_capabilities(model_name)
        return capabilities.get("supports_reasoning", False) if capabilities else False

    def get_reasoning_strength(self, model_name: str) -> Optional[ReasoningStrength]:
        """Get reasoning strength level for a model"""
        capabilities = self.get_model_capabilities(model_name)
        if capabilities:
            strength = capabilities.get("reasoning_strength")
            return strength if isinstance(strength, ReasoningStrength) else None
        return None

    def filter_reasoning_models(self, available_models: List[str]) -> List[Dict[str, Any]]:
        """Filter and rank models by reasoning capabilities"""
        reasoning_models = []

        for model_name in available_models:
            capabilities = self.get_model_capabilities(model_name)
            if capabilities and capabilities.get("supports_reasoning"):
                model_info = {
                    "name": model_name,
                    "capabilities": capabilities,
                    "reasoning_score": self._calculate_reasoning_score(capabilities)
                }
                reasoning_models.append(model_info)

        # Sort by reasoning score (highest first)
        reasoning_models.sort(key=lambda x: x["reasoning_score"], reverse=True)
        return reasoning_models

    def recommend_model_for_query(self, query: str, available_models: List[str]) -> Dict[str, Any]:
        """Recommend the best model for a specific query"""
        query_analysis = self._analyze_query_complexity(query)
        reasoning_models = self.filter_reasoning_models(available_models)

        if not reasoning_models:
            return {"error": "No reasoning-capable models available"}

        # Score each model for this specific query
        scored_models = []
        for model_info in reasoning_models:
            capabilities = model_info["capabilities"]
            query_score = self._score_model_for_query(capabilities, query_analysis)
            total_score = (model_info["reasoning_score"] * 0.7) + (query_score * 0.3)

            scored_models.append({
                **model_info,
                "query_score": query_score,
                "total_score": total_score
            })

        # Return the highest scoring model
        best_model = max(scored_models, key=lambda x: x["total_score"])

        return {
            "recommended_model": best_model["name"],
            "capabilities": best_model["capabilities"],
            "scores": {
                "reasoning": best_model["reasoning_score"],
                "query_match": best_model["query_score"],
                "total": best_model["total_score"]
            },
            "reasoning": query_analysis["reasoning_type"],
            "complexity": query_analysis["complexity"]
        }

    def get_optimal_parameters(self, model_name: str, query: str = "", deep_thinking: bool = False) -> Dict[str, Any]:
        """Get optimal parameters for a model and query"""
        capabilities = self.get_model_capabilities(model_name)
        if not capabilities:
            return self._get_default_parameters()

        base_params = {
            "temperature": capabilities.get("optimal_temperature", 0.7),
            "max_tokens": capabilities.get("max_reasoning_tokens", 4096) if deep_thinking else 2048
        }

        # Adjust for deep thinking mode
        if deep_thinking:
            base_params["temperature"] = min(base_params["temperature"], 0.4)  # More focused
            base_params["max_tokens"] = capabilities.get("max_reasoning_tokens", 4096)

        # Adjust based on query analysis
        if query:
            query_adjustments = self._get_query_based_adjustments(query, capabilities)
            base_params.update(query_adjustments)

        return base_params

    def _calculate_reasoning_score(self, capabilities: Dict[str, Any]) -> float:
        """Calculate overall reasoning score for a model"""
        score = 0.0

        # Base score from reasoning strength
        strength_scores = {
            ReasoningStrength.BASIC: 0.3,
            ReasoningStrength.ADVANCED: 0.7,
            ReasoningStrength.EXPERT: 1.0
        }
        score += strength_scores.get(capabilities.get("reasoning_strength"), 0) * 0.4

        # Score from capabilities count
        capabilities_count = len(capabilities.get("reasoning_capabilities", []))
        score += min(capabilities_count / 10, 1.0) * 0.3

        # Score from context window
        context_window = capabilities.get("context_window", 4096)
        context_score = min(context_window / 100000, 1.0)  # Normalize to 100k tokens
        score += context_score * 0.2

        # Score from structured output support
        if capabilities.get("supports_structured_output"):
            score += 0.1

        return min(score, 1.0)

    def _analyze_query_complexity(self, query: str) -> Dict[str, Any]:
        """Analyze query complexity and reasoning requirements"""
        query_lower = query.lower()
        word_count = len(query.split())

        # Determine complexity
        if word_count < 5:
            complexity = "simple"
        elif word_count < 15:
            complexity = "moderate"
        elif word_count < 30:
            complexity = "complex"
        else:
            complexity = "expert"

        # Determine reasoning type
        reasoning_indicators = {
            "analytical": ["analyze", "compare", "evaluate", "assess", "explain"],
            "creative": ["create", "design", "imagine", "innovate", "brainstorm"],
            "factual": ["what", "when", "where", "who", "how much", "fact"],
            "exploratory": ["explore", "research", "investigate", "discover", "understand"]
        }

        reasoning_type = "analytical"  # default
        max_matches = 0

        for r_type, indicators in reasoning_indicators.items():
            matches = sum(1 for indicator in indicators if indicator in query_lower)
            if matches > max_matches:
                max_matches = matches
                reasoning_type = r_type

        # Check for special indicators
        if any(word in query_lower for word in ["why", "how", "what if", "should"]):
            reasoning_type = "analytical"

        return {
            "complexity": complexity,
            "reasoning_type": reasoning_type,
            "word_count": word_count,
            "requires_web_search": any(word in query_lower for word in ["current", "latest", "news", "research", "data"]),
            "requires_calculation": any(word in query_lower for word in ["calculate", "compute", "math", "formula"])
        }

    def _score_model_for_query(self, capabilities: Dict[str, Any], query_analysis: Dict[str, Any]) -> float:
        """Score how well a model matches a specific query"""
        score = 0.0

        reasoning_capabilities = capabilities.get("reasoning_capabilities", [])

        # Score based on reasoning type match
        reasoning_type = query_analysis["reasoning_type"]
        if reasoning_type == "analytical":
            if "logical_analysis" in reasoning_capabilities or "step_by_step_reasoning" in reasoning_capabilities:
                score += 0.3
        elif reasoning_type == "creative":
            if "creative_reasoning" in reasoning_capabilities:
                score += 0.3
        elif reasoning_type == "factual":
            if "truth_seeking" in reasoning_capabilities or "factual_reasoning" in reasoning_capabilities:
                score += 0.3

        # Score based on special requirements
        if query_analysis.get("requires_web_search"):
            if "web_search" in reasoning_capabilities or "real_time_knowledge" in reasoning_capabilities:
                score += 0.2

        if query_analysis.get("requires_calculation"):
            if "mathematical_reasoning" in reasoning_capabilities or "calculation" in reasoning_capabilities:
                score += 0.2

        # Score based on complexity match
        complexity = query_analysis["complexity"]
        strength = capabilities.get("reasoning_strength")

        if complexity == "expert" and strength == ReasoningStrength.EXPERT:
            score += 0.3
        elif complexity in ["complex", "moderate"] and strength in [ReasoningStrength.ADVANCED, ReasoningStrength.EXPERT]:
            score += 0.2
        elif complexity == "simple" and strength != ReasoningStrength.BASIC:
            score += 0.1  # Advanced models can handle simple queries well

        return min(score, 1.0)

    def _get_query_based_adjustments(self, query: str, capabilities: Dict[str, Any]) -> Dict[str, Any]:
        """Get parameter adjustments based on query analysis"""
        query_analysis = self._analyze_query_complexity(query)
        adjustments = {}

        # Adjust temperature based on reasoning type
        reasoning_type = query_analysis["reasoning_type"]
        base_temp = capabilities.get("optimal_temperature", 0.7)

        if reasoning_type == "factual":
            adjustments["temperature"] = min(base_temp, 0.2)
        elif reasoning_type == "creative":
            adjustments["temperature"] = max(base_temp, 0.6)
        elif reasoning_type == "analytical":
            adjustments["temperature"] = min(base_temp, 0.4)

        # Adjust max tokens based on complexity
        complexity = query_analysis["complexity"]
        base_max_tokens = capabilities.get("max_reasoning_tokens", 4096)

        if complexity == "expert":
            adjustments["max_tokens"] = min(base_max_tokens, 16384)
        elif complexity == "complex":
            adjustments["max_tokens"] = min(base_max_tokens, 8192)
        elif complexity == "moderate":
            adjustments["max_tokens"] = min(base_max_tokens, 4096)

        return adjustments

    def _get_default_parameters(self) -> Dict[str, Any]:
        """Get default parameters for unknown models"""
        return {
            "temperature": 0.7,
            "max_tokens": 2048,
            "supports_reasoning": False
        }

    def get_models_by_capability(self, capability: str, available_models: List[str]) -> List[str]:
        """Get models that support a specific capability"""
        matching_models = []

        for model_name in available_models:
            capabilities = self.get_model_capabilities(model_name)
            if capabilities and capability in capabilities.get("reasoning_capabilities", []):
                matching_models.append(model_name)

        return matching_models

    def get_model_limitations(self, model_name: str) -> List[str]:
        """Get known limitations for a model"""
        capabilities = self.get_model_capabilities(model_name)
        return capabilities.get("limitations", []) if capabilities else []


# Global instance
model_capabilities = ModelCapabilities()


# Convenience functions
def get_reasoning_models(available_models: List[str]) -> List[Dict[str, Any]]:
    """Get all reasoning-capable models with their capabilities"""
    return model_capabilities.filter_reasoning_models(available_models)


def recommend_model_for_query(query: str, available_models: List[str]) -> Dict[str, Any]:
    """Recommend the best model for a query"""
    return model_capabilities.recommend_model_for_query(query, available_models)


def get_optimal_parameters(model_name: str, query: str = "", deep_thinking: bool = False) -> Dict[str, Any]:
    """Get optimal parameters for a model and query"""
    return model_capabilities.get_optimal_parameters(model_name, query, deep_thinking)


def is_model_reasoning_capable(model_name: str) -> bool:
    """Check if a model supports reasoning"""
    return model_capabilities.is_reasoning_capable(model_name)
