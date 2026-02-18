"""Hybrid BM25 + dense retrieval."""
from rank_bm25 import BM25Okapi
from typing import List, Dict

class HybridSearcher:
    def __init__(self):
        self.bm25 = None
        self.corpus = []
    
    def index_corpus(self, documents: List[str]):
        """Index documents for BM25."""
        if not documents:
            return
        tokenized = [doc.split() for doc in documents]
        self.bm25 = BM25Okapi(tokenized)
        self.corpus = documents
    
    def search(self, query: str, top_k: int = 15) -> List[str]:
        """BM25 sparse retrieval."""
        if not self.bm25 or not self.corpus:
            return []
        
        tokenized_query = query.split()
        scores = self.bm25.get_scores(tokenized_query)
        
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [self.corpus[i] for i in top_indices]
    
    def merge_results(self, dense_results: List[str], sparse_results: List[str]) -> List[str]:
        """Reciprocal Rank Fusion."""
        def rrf_score(rank, k=60):
            return 1.0 / (k + rank)
        
        scores = {}
        
        # Deduplicate and score
        for rank, doc in enumerate(dense_results):
            scores[doc] = scores.get(doc, 0) + rrf_score(rank)
        
        for rank, doc in enumerate(sparse_results):
            scores[doc] = scores.get(doc, 0) + rrf_score(rank)
        
        merged = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [doc for doc, score in merged]
