import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Pricing (USD per 1M tokens) - Update as needed
PRICING = {
    "gpt-4o": {"input": 5.00, "output": 15.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    # Anthropic
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
}

class TokenService:
    def __init__(self):
        self.encoding = None
        try:
            import tiktoken
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except ImportError:
            logger.warning("tiktoken not installed. Using approximation.")
        except Exception as e:
            logger.warning(f"Failed to load tiktoken: {e}")

    def count_tokens(self, text: str, model: str = "gpt-4o") -> int:
        """
        Count tokens for a given text string.
        """
        if not text:
            return 0
            
        if self.encoding:
            try:
                # Most modern models use cl100k_base
                return len(self.encoding.encode(text))
            except Exception as e:
                logger.error(f"Token counting error: {e}")
        
        # Fallback approximation (avg 4 chars per token)
        return len(text) // 4

    def calculate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        """
        Calculate estimated cost in USD.
        """
        # Normalize model name (remove specific versions like -0613)
        base_model = model
        for key in PRICING:
            if key in model:
                base_model = key
                break
        
        rates = PRICING.get(base_model)
        if not rates:
            return 0.0
            
        input_cost = (input_tokens / 1_000_000) * rates["input"]
        output_cost = (output_tokens / 1_000_000) * rates["output"]
        
        return round(input_cost + output_cost, 6)

# Global instance
token_service = TokenService()
