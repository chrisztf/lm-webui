"""Nomic embedder wrapper with validation."""
from sentence_transformers import SentenceTransformer
import torch
import torch.nn.functional as F
import numpy as np
import os
import logging
from typing import List, Optional
from app.services.model_validator import get_model_validator
from app.hardware.service import get_torch_settings

logger = logging.getLogger(__name__)

class NomicEmbedder:
    def __init__(self, validate_before_load: bool = True):
        """
        Initialize Nomic embedder with validation
        
        Args:
            validate_before_load: Whether to validate disk space and cache before loading
        """
        self.model_id = 'nomic-ai/nomic-embed-text-v1.5'
        self.cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../rag/embed"))
        self.model = None
        self.model_validator = get_model_validator()
        self.validate_before_load = validate_before_load
        
        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # self._load_model()
    
    def _load_model(self):
        """Load Nomic embedder model with validation and error handling"""
        try:
            # Validate before loading if enabled
            if self.validate_before_load:
                validation = self.model_validator.validate_model_download(
                    model_id=self.model_id,
                    model_type="embedding",
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
            
            logger.info(f"Loading Nomic embedder model from {self.model_id}")
            logger.info(f"Cache directory: {self.cache_dir}")
            
            # Get optimized PyTorch settings from unified hardware manager
            torch_settings = get_torch_settings()
            device = torch_settings["device"]
            logger.info(f"Embedder loading on device: {device}")
            logger.info(f"PyTorch settings: dtype={torch_settings.get('dtype', 'float32')}, "
                       f"allow_tf32={torch_settings.get('allow_tf32', False)}")

            # Determine if we can use local files only
            local_files_only = False
            try:
                cache_check = self.model_validator.validate_model_cache(self.model_id, self.cache_dir)
                if cache_check.get("has_files", False):
                    local_files_only = True
                    logger.info("Nomic embedder found in cache, skipping network checks")
            except Exception:
                pass

            # Load the model with sentence-transformers
            self.model = SentenceTransformer(
                self.model_id, 
                trust_remote_code=True,
                cache_folder=self.cache_dir,
                device=device,
                local_files_only=local_files_only
            )
            
            logger.info("Nomic embedder model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load Nomic embedder model: {e}")
            self.model = None
            raise RuntimeError(f"Failed to load embedding model: {e}")
    
    def encode(self, texts: List[str], task_type: str = "search_document", dimensionality: int = 512) -> np.ndarray:
        """
        Encode texts to embeddings with Matryoshka support.
        
        Args:
            texts: List of text strings to encode
            task_type: Task prefix ('search_document', 'search_query', 'clustering', 'classification')
            dimensionality: Output dimension (default: 512 for Matryoshka)
            
        Returns:
            Numpy array of embeddings
        """
        if self.model is None:
            self._load_model()

        if self.model is None:
            raise RuntimeError("Embedding model not initialized")
            
        try:
            # Add task prefix
            prefixed_texts = [f"{task_type}: {t}" for t in texts]
            
            # Encode with PyTorch tensor output for Matryoshka operations
            embeddings = self.model.encode(prefixed_texts, convert_to_tensor=True)
            
            # Matryoshka embedding logic (LayerNorm -> Slice -> Normalize)
            # 1. Layer Norm
            embeddings = F.layer_norm(embeddings, normalized_shape=(embeddings.shape[1],))
            
            # 2. Slice to desired dimension if specified
            if dimensionality and dimensionality < embeddings.shape[1]:
                embeddings = embeddings[:, :dimensionality]
            
            # 3. L2 Normalize
            embeddings = F.normalize(embeddings, p=2, dim=1)
            
            # Convert back to numpy
            if hasattr(embeddings, "cpu"):
                return embeddings.cpu().numpy()
            return embeddings.numpy()
            
        except Exception as e:
            logger.error(f"Failed to encode texts: {e}")
            raise RuntimeError(f"Embedding failed: {e}")
    
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
            "embedding_dimension": self.model.get_sentence_embedding_dimension() if hasattr(self.model, 'get_sentence_embedding_dimension') else "unknown"
        }
        
        # Add validation info
        try:
            validation = self.model_validator.validate_model_cache(self.model_id, self.cache_dir)
            info["cache_validation"] = validation
        except Exception as e:
            info["cache_validation_error"] = str(e)
        
        return info
    
    def encode_batch(self, texts: List[str], batch_size: int = 32, task_type: str = "search_document", dimensionality: int = 512) -> np.ndarray:
        """
        Encode texts in batches with Matryoshka support.
        
        Args:
            texts: List of text strings to encode
            batch_size: Batch size for encoding
            task_type: Task prefix ('search_document', 'search_query', etc.)
            dimensionality: Output dimension
            
        Returns:
            Numpy array of embeddings
        """
        if self.model is None:
            self._load_model()

        if self.model is None:
            raise RuntimeError("Embedding model not initialized")
            
        try:
            # Add task prefix to all texts
            prefixed_texts = [f"{task_type}: {t}" for t in texts]
            
            # Process in batches to manage memory
            all_embeddings = []
            
            for i in range(0, len(prefixed_texts), batch_size):
                batch = prefixed_texts[i:i + batch_size]
                
                # Encode batch
                batch_embeddings = self.model.encode(batch, convert_to_tensor=True)
                
                # Matryoshka operations
                batch_embeddings = F.layer_norm(batch_embeddings, normalized_shape=(batch_embeddings.shape[1],))
                
                if dimensionality and dimensionality < batch_embeddings.shape[1]:
                    batch_embeddings = batch_embeddings[:, :dimensionality]
                    
                batch_embeddings = F.normalize(batch_embeddings, p=2, dim=1)
                
                # Convert to numpy
                if hasattr(batch_embeddings, "cpu"):
                    batch_embeddings = batch_embeddings.cpu().numpy()
                else:
                    batch_embeddings = batch_embeddings.numpy()
                    
                all_embeddings.append(batch_embeddings)
            
            return np.vstack(all_embeddings)
            
        except Exception as e:
            logger.error(f"Failed to encode batch: {e}")
            raise RuntimeError(f"Batch embedding failed: {e}")
