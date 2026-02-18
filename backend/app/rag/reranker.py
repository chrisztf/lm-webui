"""BGE reranker wrapper with validation - using lightweight base model."""
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch
import os
import logging
from typing import List, Tuple, Optional
from app.services.model_validator import get_model_validator
from app.hardware.service import get_torch_settings

logger = logging.getLogger(__name__)

class BGEReranker:
    def __init__(self, validate_before_load: bool = True):
        """
        Initialize BGE reranker with validation
        
        Args:
            validate_before_load: Whether to validate disk space and cache before loading
        """
        # Use lightweight base model instead of large v2-m3
        self.model_id = 'BAAI/bge-reranker-base'
        self.cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../rag/rerank"))
        self.model = None
        self.model_validator = get_model_validator()
        self.validate_before_load = validate_before_load
        
        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # self._load_model()
    
    def _load_model(self):
        """Load BGE reranker model with validation and error handling"""
        try:
            # Validate before loading if enabled
            if self.validate_before_load:
                validation = self.model_validator.validate_model_download(
                    model_id=self.model_id,
                    model_type="reranker",
                    target_dir=self.cache_dir
                )
                
                if not validation.get("can_proceed", False):
                    logger.warning(f"Model validation failed: {validation.get('blocking_reasons', ['Unknown'])}")
                    # Check if model already exists in cache
                    cache_check = self.model_validator.validate_model_cache(self.model_id, self.cache_dir)
                    if cache_check.get("has_files", False):
                        logger.info(f"Using cached model files: {cache_check.get('file_count', 0)} files found")
                    else:
                        raise RuntimeError(f"Cannot load model: {validation.get('blocking_reasons', ['Validation failed'])}")
            
            logger.info(f"Loading reranker model: {self.model_id}")
            logger.info(f"Cache directory: {self.cache_dir}")
            
            # Get optimized PyTorch settings from unified hardware manager
            torch_settings = get_torch_settings()
            device = torch_settings["device"]
            logger.info(f"Reranker loading on device: {device}")
            logger.info(f"PyTorch settings: dtype={torch_settings.get('dtype', 'float32')}")

            # Determine if we can use local files only
            local_files_only = False
            try:
                cache_check = self.model_validator.validate_model_cache(self.model_id, self.cache_dir)
                if cache_check.get("has_files", False):
                    local_files_only = True
                    logger.info("Reranker found in cache, skipping network checks")
            except Exception:
                pass

            # Load the model with transformers (matching official doc)
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_id,
                cache_dir=self.cache_dir,
                local_files_only=local_files_only
            )
            
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.model_id,
                cache_dir=self.cache_dir,
                local_files_only=local_files_only
            )
            self.model.eval()
            self.model.to(device)
            
            logger.info(f"Reranker model loaded successfully from {self.cache_dir}")
            
        except Exception as e:
            logger.error(f"Failed to load reranker model: {e}")
            self.model = None
            raise RuntimeError(f"Failed to load reranker model: {e}")
    
    def rerank(self, query: str, documents: List[str], top_k: int = 3) -> List[Tuple[float, str]]:
        """
        Rerank documents by relevance.
        
        Args:
            query: Search query
            documents: List of document strings to rerank
            top_k: Number of top documents to return
            
        Returns:
            List of tuples (score, document) sorted by score descending
        """
        if self.model is None:
            self._load_model()

        if self.model is None:
            raise RuntimeError("Reranker model not initialized")
            
        if not documents:
            return []
            
        try:
            # Create query-document pairs
            pairs = [[query, doc] for doc in documents]
            
            # Compute scores (matching official doc implementation)
            with torch.no_grad():
                inputs = self.tokenizer(
                    pairs, 
                    padding=True, 
                    truncation=True, 
                    return_tensors='pt', 
                    max_length=512
                )
                inputs = inputs.to(self.model.device)
                scores = self.model(**inputs, return_dict=True).logits.view(-1, ).float()
                
                # Convert to list
                if hasattr(scores, "cpu"):
                    scores = scores.cpu().numpy().tolist()
                else:
                    scores = scores.numpy().tolist()
            
            # Rank documents by score
            ranked = sorted(zip(scores, documents), reverse=True)
            
            # Return top_k results
            return ranked[:top_k]
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            # Return documents in original order as fallback
            return [(0.0, doc) for doc in documents[:top_k]]
    
    def rerank_with_scores(self, query: str, documents: List[str]) -> List[Tuple[float, str]]:
        """
        Rerank documents and return all scores.
        
        Args:
            query: Search query
            documents: List of document strings to rerank
            
        Returns:
            List of tuples (score, document) sorted by score descending
        """
        if self.model is None:
            self._load_model()

        if self.model is None:
            raise RuntimeError("Reranker model not initialized")
            
        if not documents:
            return []
            
        try:
            pairs = [[query, doc] for doc in documents]
            
            with torch.no_grad():
                inputs = self.tokenizer(
                    pairs, 
                    padding=True, 
                    truncation=True, 
                    return_tensors='pt', 
                    max_length=512
                )
                inputs = inputs.to(self.model.device)
                scores = self.model(**inputs, return_dict=True).logits.view(-1, ).float()
                
                if hasattr(scores, "cpu"):
                    scores = scores.cpu().numpy().tolist()
                else:
                    scores = scores.numpy().tolist()
            
            return sorted(zip(scores, documents), reverse=True)
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return [(0.0, doc) for doc in documents]
    
    def is_loaded(self) -> bool:
        """Check if the model is loaded successfully"""
        return self.model is not None
    
    def get_model_info(self) -> dict:
        """Get information about the loaded model"""
        if not self.is_loaded():
            return {"status": "not_loaded"}
        
        info = {
            "status": "loaded",
            "model_id": self.model_id,
            "cache_dir": self.cache_dir,
            "model_type": "cross-encoder"
        }
        
        # Add validation info
        try:
            validation = self.model_validator.validate_model_cache(self.model_id, self.cache_dir)
            info["cache_validation"] = validation
        except Exception as e:
            info["cache_validation_error"] = str(e)
        
        return info
    
    def batch_rerank(self, queries: List[str], documents_list: List[List[str]], top_k: int = 3) -> List[List[Tuple[float, str]]]:
        """
        Rerank multiple queries with their respective documents.
        
        Args:
            queries: List of search queries
            documents_list: List of document lists (one per query)
            top_k: Number of top documents to return per query
            
        Returns:
            List of ranked results per query
        """
        if self.model is None:
            self._load_model()

        if self.model is None:
            raise RuntimeError("Reranker model not initialized")
            
        if len(queries) != len(documents_list):
            raise ValueError("Number of queries must match number of document lists")
            
        results = []
        for query, documents in zip(queries, documents_list):
            try:
                ranked = self.rerank(query, documents, top_k)
                results.append(ranked)
            except Exception as e:
                logger.error(f"Batch reranking failed for query '{query}': {e}")
                # Fallback: return documents in original order
                results.append([(0.0, doc) for doc in documents[:top_k]])
        
        return results
