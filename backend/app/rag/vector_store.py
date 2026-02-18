"""Qdrant vector store wrapper for Dual-Layer Memory."""
from qdrant_client import QdrantClient, models
from qdrant_client.models import Distance, VectorParams, PointStruct
from typing import List, Dict, Any, Optional
import uuid
import os
from pathlib import Path

# Global Singleton to prevent multiple file locks
_shared_client: Optional[QdrantClient] = None
_shared_path: Optional[str] = None

def get_base_dir() -> Path:
    """Get consistent base directory (backend/) for path calculations."""
    return Path(__file__).resolve().parent.parent.parent

class QdrantStore:
    def __init__(self, path: str = None, collection_name: str = "documents"):
        global _shared_client, _shared_path
        
        # Default to a local path if not provided
        if path is None:
            # Check env var first
            data_dir = os.getenv("DATA_DIR")
            base_dir = get_base_dir()
            
            if data_dir:
                if os.path.isabs(data_dir):
                     path = os.path.join(data_dir, "qdrant_db")
                else:
                     # Handle relative path by joining with base_dir
                     path = str(base_dir / data_dir / "qdrant_db")
            else:
                path = str(base_dir / "data" / "qdrant_db")
        
        # Ensure the path is absolute
        if not os.path.isabs(path):
            path = str(base_dir / path)
        
        # Singleton Logic: Reuse existing client if path matches
        if _shared_client is None:
            print(f"Initializing Shared Qdrant Client at: {path}")
            _shared_client = QdrantClient(path=path)
            _shared_path = path
        elif path != _shared_path:
            print(f"Warning: Requesting Qdrant at {path} but shared client is at {_shared_path}. Using separate instance (Risk of Lock Error).")
            # If paths differ significantly, we might be forced to create a new one, 
            # but usually this indicates a configuration mismatch.
            # Ideally we should error out or force use of shared if possible.
            # For now, we try to use the new path, but warn.
            self.client = QdrantClient(path=path)
        
        # Use the shared client
        if _shared_client:
            self.client = _shared_client
            
        self.collection_name = collection_name
        self._init_collection()
    
    def _init_collection(self):
        try:
            collections = self.client.get_collections().collections
            if not any(c.name == self.collection_name for c in collections):
                print(f"Creating Qdrant collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=768, distance=Distance.COSINE)
                )
        except Exception as e:
            print(f"Error initializing Qdrant collection {self.collection_name}: {e}")

    def add(self, texts: List[str], embeddings: List[List[float]], 
            metadatas: List[Dict], ids: List[str] = None):
        """Add vectors to the store."""
        if not texts:
            return
            
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in texts]
        
        points = [
            PointStruct(
                id=id_,
                vector=embedding,
                payload={"text": text, **metadata}
            )
            for id_, text, embedding, metadata in zip(ids, texts, embeddings, metadatas)
        ]
        
        self.client.upsert(collection_name=self.collection_name, points=points)

    def query(self, query_embedding: List[float], conversation_id: str = None, top_k: int = 15, user_id: int = None) -> List[Dict]:
        """
        Versatile query method for RAG and Memory.
        """
        filters = []
        if conversation_id and conversation_id != "global":
            filters.append(models.FieldCondition(key="conversation_id", match=models.MatchValue(value=conversation_id)))
        
        if user_id:
             filters.append(models.FieldCondition(key="user_id", match=models.MatchValue(value=user_id)))

        filter_condition = models.Filter(must=filters) if filters else None

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
            query_filter=filter_condition
        )
        
        return [
            {
                "content": hit.payload.get("text", ""),
                "metadata": hit.payload,
                "score": hit.score,
                "id": hit.id
            }
            for hit in results
        ]

    def get_all_for_conversation(self, conversation_id: str) -> List[str]:
        """Retrieve all document texts for BM25 indexing."""
        try:
            points, _ = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[models.FieldCondition(key="conversation_id", match=models.MatchValue(value=conversation_id))]
                ),
                limit=10000,
                with_payload=True,
                with_vectors=False
            )
            return [p.payload.get("text", "") for p in points]
        except Exception as e:
            print(f"Error getting conversation docs: {e}")
            return []

    def get_files(self, file_names: List[str], conversation_id: str) -> List[Dict]:
        """Retrieve specific files by name."""
        if not file_names:
            return []
            
        should_conditions = [
            models.FieldCondition(key="file_name", match=models.MatchValue(value=name))
            for name in file_names
        ]
        
        try:
            points, _ = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[models.FieldCondition(key="conversation_id", match=models.MatchValue(value=conversation_id))],
                    should=should_conditions if should_conditions else None
                ),
                limit=1000,
                with_payload=True
            )
            return [
                {
                    "content": p.payload.get("text", ""),
                    "metadata": p.payload,
                    "id": p.id
                }
                for p in points
            ]
        except Exception as e:
            print(f"Error getting files: {e}")
            return []
            
    def delete_conversation(self, conversation_id: str):
        """Delete all vectors for a conversation."""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[models.FieldCondition(key="conversation_id", match=models.MatchValue(value=conversation_id))]
                    )
                )
            )
        except Exception as e:
            print(f"Error deleting conversation {conversation_id}: {e}")
