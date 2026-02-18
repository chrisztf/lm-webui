"""Contextual chunking utilities."""
from typing import List

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Split text into overlapping chunks while preserving structure.
    Uses paragraph-aware splitting to avoid breaking semantic context.
    """
    if not text:
        return []
    
    # Normalize line endings
    text = text.replace('\r\n', '\n')
    
    # Split by double newline to preserve paragraphs
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = []
    current_length = 0
    
    # Helper to finalize a chunk
    def add_chunk(words_list):
        if words_list:
            chunks.append(" ".join(words_list))
    
    for paragraph in paragraphs:
        # Split paragraph into words but preserve some internal structure if needed
        # For simplicity, we treat paragraphs as units.
        para_words = paragraph.split()
        if not para_words:
            continue
            
        # If a single paragraph is too large, split it
        if len(para_words) > chunk_size:
            # Add accumulated chunk first
            if current_chunk:
                add_chunk(current_chunk)
                current_chunk = []
                current_length = 0
            
            # Split the large paragraph
            for i in range(0, len(para_words), chunk_size - overlap):
                chunk_part = para_words[i:i + chunk_size]
                add_chunk(chunk_part)
            continue
            
        # If adding this paragraph exceeds size, save current chunk and start new
        if current_length + len(para_words) > chunk_size:
            add_chunk(current_chunk)
            
            # Handle overlap: keep last 'overlap' words for context
            if overlap > 0 and len(current_chunk) > overlap:
                current_chunk = current_chunk[-overlap:]
                current_length = len(current_chunk)
            else:
                current_chunk = []
                current_length = 0
        
        current_chunk.extend(para_words)
        current_length += len(para_words)
        
    # Add final chunk
    if current_chunk:
        add_chunk(current_chunk)
    
    return chunks

def add_context_to_chunks(chunks: List[str], doc_summary: str, file_name: str) -> List[str]:
    """Add document context to each chunk."""
    contextual_chunks = []
    
    for i, chunk in enumerate(chunks):
        # stronger anchoring with [Source: filename] format
        prefix = f"[Source: {file_name}]\nDocument Summary: {doc_summary}\nContent Section {i+1}:\n\n"
        contextual_chunks.append(prefix + chunk)
    
    return contextual_chunks

def generate_summary(text: str, max_words: int = 50) -> str:
    """Simple extractive summary (first N words)."""
    words = text.split()[:max_words]
    return " ".join(words) + "..."
