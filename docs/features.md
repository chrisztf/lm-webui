# Features

## Overview

LM WebUI is a comprehensive multimodal LLM interface with a wide range of features designed for privacy-first, fully offline AI workflows. This document provides detailed information about all available features.

## Core Features

### 1. 🔐 Authentication & User Management

#### JWT-Based Authentication

- **Stateless authentication** using JSON Web Tokens
- **Refresh tokens** stored as HTTP-only cookies for security
- **Role-based access control** with user and admin levels
- **Session isolation** ensuring conversation privacy

#### User Management

- User registration and login
- Session management with automatic expiration
- Conversation isolation per user
- Secure password hashing with bcrypt

#### Security Features

- Input validation and sanitization
- Rate limiting protection
- CSRF protection
- Secure cookie handling

### 2. 🌐 WebSocket Streaming with Reasoning

#### Real-time Communication

- **Bidirectional WebSocket communication** for instant updates
- **Token-by-token streaming** with controlled pacing (1-2 tokens per message)
- **Connection health monitoring** with automatic reconnection
- **Heartbeat mechanism** to detect and recover from disconnections

#### Interactive Reasoning Display

- **Step-by-step reasoning visualization** showing AI thinking process
- **Expandable reasoning steps** with confidence scores
- **Real-time progress indicators** during generation
- **Visual thinking animations** for better user experience

#### Streaming Control

- **Immediate cancellation** with state preservation
- **Stop/resume functionality** during generation
- **Session management** for concurrent streams
- **Resource cleanup** on connection close

### 3. 🔗 RAG (Retrieval-Augmented Generation)

#### Vector Store Integration

- **Qdrant vector database** for efficient similarity search
- **Automatic embedding generation** for text and documents
- **Metadata storage** for source attribution and versioning
- **Index optimization** for fast retrieval

#### Context Management

- **Intelligent context window management** with token optimization
- **Cross-conversation retrieval** of relevant historical context
- **File reference integration** for multimodal content
- **Automatic context pruning** to stay within model limits

#### Retrieval Pipeline

- **Semantic search** across conversation history
- **Hybrid search** combining semantic and keyword matching
- **Relevance scoring** with configurable thresholds
- **Source attribution** showing where information came from

### 4. 👁️ Multimodal Processing

#### Image Processing

- **Image upload and validation** (PNG, JPG, WebP formats)
- **Automatic resizing and optimization** for LLM consumption
- **OCR text extraction** using EasyOCR integration
- **Base64 encoding** for seamless LLM integration
- **Metadata extraction** (dimensions, format, size)

#### Document Processing

- **PDF parsing** with pypdf for text extraction
- **DOCX processing** with python-docx integration
- **Content summarization** for large documents
- **Structured data preparation** for LLM context
- **File size limits** with intelligent truncation

#### Multimodal Integration

- **Automatic context inclusion** of file content in conversations
- **File reference tracking** across conversations
- **Thumbnail generation** for visual previews
- **Progress tracking** during file processing

### 5. ⚡ Hardware Acceleration

#### Automatic Detection

- **CUDA detection** for NVIDIA GPUs with VRAM measurement
- **ROCm detection** for AMD GPUs on Linux systems
- **Metal detection** for Apple Silicon Macs
- **CPU fallback** with optimization recommendations
- **Cross-platform compatibility** checks

#### Intelligent Quantization

- **VRAM-aware quantization selection** based on available memory
- **Backend-specific quantization hierarchies** for optimal performance
- **Automatic fallback** to CPU-safe options when needed
- **Performance optimization** based on hardware capabilities

#### Optimization Features

- **Model loading optimization** for available hardware
- **Memory management** with automatic cleanup
- **Performance monitoring** with real-time feedback
- **Hardware utilization display** in UI

### 6. 🤖 GGUF Runtime & Model Management ⭐

#### Complete GGUF Integration

- **GGUF model management system** with full API support
- **HuggingFace integration** for direct model downloads
- **Local model registry** for organizing GGUF files
- **Hardware compatibility checking** before model usage

#### Model Operations

- **Upload GGUF models** from local storage
- **Download from HuggingFace** with progress tracking
- **Model validation** ensuring file integrity
- **Metadata extraction** from GGUF files
- **Model deletion** with cleanup

#### WebSocket Progress Tracking

- **Real-time download progress** via WebSocket
- **Cancelable downloads** with cleanup
- **Progress visualization** in UI
- **Error handling** with user feedback

#### API Endpoints

- `POST /api/gguf/resolve` - Resolve model from HuggingFace
- `POST /api/gguf/download` - Download GGUF model
- `WS /api/gguf/download/{task_id}` - WebSocket progress tracking
- `GET /api/gguf/local` - List local models
- `POST /api/gguf/upload` - Upload GGUF model
- `DELETE /api/gguf/{model_name}` - Delete model
- `GET /api/gguf/compatibility/{model_name}` - Check hardware compatibility

#### Usage Examples

```bash
# Download a model from HuggingFace
curl -X POST http://localhost:8000/api/gguf/download \
  -H "Content-Type: application/json" \
  -d '{
    "file_url": "https://huggingface.co/TheBloke/Llama-2-7B-GGUF/resolve/main/llama-2-7b.Q4_K_M.gguf",
    "filename": "llama-2-7b.Q4_K_M.gguf"
  }'

# List local models
curl http://localhost:8000/api/gguf/local

# Check compatibility
curl http://localhost:8000/api/gguf/compatibility/llama-2-7b.Q4_K_M.gguf
```

### 7. 🧠 Knowledge Graph & Memory System

#### Conversation Memory

- **Persistent conversation storage** with relationship tracking
- **Entity extraction** and relationship mapping
- **Semantic linking** between related conversations
- **Memory consolidation** over time

#### Knowledge Organization

- **Topic clustering** for better organization
- **Cross-reference creation** between related content
- **Temporal tracking** of conversation evolution
- **Import/export functionality** for knowledge transfer

#### Search Capabilities

- **Semantic search** across stored knowledge
- **Relationship traversal** through connected entities
- **Context-aware retrieval** based on current conversation
- **Relevance ranking** of retrieved memories

### 8. 🔍 Semantic Search

#### Vector Search

- **Embedding-based similarity search** across all content
- **Multi-modal search** supporting text, images, and documents
- **Hybrid search** combining vector and keyword matching
- **Relevance scoring** with configurable weights

#### Search Features

- **Cross-conversation search** finding relevant historical context
- **File content search** within uploaded documents and images
- **Real-time indexing** of new content
- **Search result highlighting** showing matches

#### Performance Optimization

- **Index optimization** for fast retrieval
- **Caching mechanism** for frequent queries
- **Batch processing** for large datasets
- **Memory-efficient storage** of embeddings

### 9. 📱 Real-time Features

#### Live Updates

- **Real-time title generation** as conversations progress
- **Conversation synchronization** across multiple devices
- **WebSocket event system** for instant notifications
- **Status monitoring** with health checks

#### User Experience

- **Typing indicators** showing when AI is thinking
- **Progress bars** for long operations
- **Toast notifications** for important events
- **Error reporting** with helpful messages

#### System Monitoring

- **Resource usage tracking** (CPU, memory, GPU)
- **Performance metrics** collection
- **Error logging** and aggregation
- **Health check endpoints** for monitoring

### 10. 🏠 Deployment & Infrastructure

#### Self-Hosted Ready

- **Docker containerization** for easy deployment
- **Docker Compose setup** for complete stack
- **Kubernetes manifests** for production deployment
- **Environment-based configuration** for different setups

#### Database Support

- **SQLite** for development and simple deployments
- **PostgreSQL** for production with concurrent users
- **Database migrations** for schema updates
- **Connection pooling** for performance

#### Security Features

- **Environment variable configuration** for secrets
- **API key encryption** with AES-256
- **Secure defaults** for production deployment
- **CORS configuration** for frontend-backend communication

## Feature Integration

### How Features Work Together

1. **User Authentication** → **Conversation Context** → **RAG Retrieval** → **AI Response**
2. **File Upload** → **Multimodal Processing** → **Context Integration** → **Enhanced Responses**
3. **GGUF Download** → **Hardware Compatibility Check** → **Model Loading** → **Local Inference**
4. **WebSocket Connection** → **Real-time Streaming** → **Interactive Reasoning** → **User Feedback**

### Configuration Options

Each feature can be configured through:

- **Environment variables** for deployment-specific settings
- **Configuration files** (`config.yaml`) for application settings
- **UI settings** for user preferences
- **API parameters** for runtime customization

## Performance Characteristics

### Response Times

- **Authentication**: < 50ms
- **WebSocket connection**: < 100ms
- **RAG retrieval**: < 200ms for typical queries
- **Image processing**: < 2s for standard images
- **GGUF download**: Variable based on file size and network

### Resource Usage

- **Memory**: ~500MB base + model memory
- **CPU**: Minimal when idle, scales with usage
- **GPU**: Optional, used when available for acceleration
- **Storage**: Configurable based on conversation history and models

## Compatibility

### Supported Platforms

- **Operating Systems**: Linux, macOS, Windows (WSL2 recommended)
- **Browsers**: Chrome, Firefox, Safari, Edge (modern versions)
- **Python**: 3.9+
- **Node.js**: 16+

### Hardware Requirements

- **Minimum**: 4GB RAM, 10GB storage
- **Recommended**: 8GB+ RAM, 20GB+ storage, GPU for acceleration
- **Production**: 16GB+ RAM, 50GB+ storage, dedicated GPU

## Getting Help

For more information about specific features:

- See [API Reference](./api-reference.md) for endpoint details
- Check [Deployment Guide](./deployment.md) for setup instructions
- Visit [Troubleshooting](./troubleshooting.md) for common issues
- Join [GitHub Discussions](https://github.com/lm-webui/lm-webui/discussions) for community support
