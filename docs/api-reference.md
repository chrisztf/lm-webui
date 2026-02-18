# API Reference

LM WebUI provides a comprehensive REST API and WebSocket interface for AI model management, chat, and multimodal processing.

## Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://your-domain.com`

## Authentication

Most endpoints require JWT authentication. Include the token in the Authorization header:

```http
Authorization: Bearer <your_jwt_token>
```

Tokens are obtained through the `/api/auth/login` endpoint and refreshed automatically via HTTP-only cookies.

## API Endpoints

### Authentication

#### POST `/api/auth/register`

Register a new user.

**Request:**

```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response:**

```json
{
  "message": "User created successfully",
  "user_id": 1
}
```

#### POST `/api/auth/login`

Login and obtain JWT tokens.

**Request:**

```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response:**

- Sets HTTP-only cookies: `access_token` and `refresh_token`
- Returns user information

#### POST `/api/auth/refresh`

Refresh access token using refresh token cookie.

**Response:**

- Sets new `access_token` cookie
- Returns new token information

#### POST `/api/auth/logout`

Logout and clear tokens.

### Chat

#### POST `/api/chat`

Send a chat message.

**Request:**

```json
{
  "message": "Hello, how are you?",
  "conversation_id": "optional-conversation-id",
  "provider": "openai",
  "model": "gpt-4o-mini",
  "temperature": 0.7,
  "max_tokens": 1000,
  "use_rag": true,
  "deep_thinking_mode": false,
  "show_raw_response": false
}
```

**Response:**

```json
{
  "response": "Hello! I'm doing well, thank you for asking!",
  "conversation_id": "conv_123456789",
  "tokens_used": 45,
  "processing_time": 1.23
}
```

#### POST `/api/chat/stream/start`

Start a streaming chat session.

**Request:** Same as `/api/chat`

**Response:**

```json
{
  "session_id": "session_123456789",
  "websocket_url": "/ws/chat/session_123456789"
}
```

#### WebSocket `/ws/chat`

Real-time streaming chat endpoint.

**Connection:**

```javascript
const ws = new WebSocket("ws://localhost:8000/ws/chat");

ws.onopen = () => {
  ws.send(
    JSON.stringify({
      action: "start_stream",
      data: {
        message: "Hello AI",
        provider: "openai",
        model: "gpt-4o-mini",
      },
    }),
  );
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.type, data.content);
};
```

**Event Types:**

- `reasoning_step`: AI thinking step
- `token_update`: New token in stream
- `final_answer`: Complete response
- `error`: Error occurred
- `cancelled`: Stream cancelled

### GGUF Model Management

#### POST `/api/gguf/resolve`

Resolve a GGUF model from HuggingFace.

**Request:**

```json
{
  "input": "TheBloke/Llama-2-7B-GGUF:llama-2-7b.Q4_K_M.gguf"
}
```

**Response:**

```json
{
  "resolved": true,
  "filename": "llama-2-7b.Q4_K_M.gguf",
  "url": "https://huggingface.co/TheBloke/Llama-2-7B-GGUF/resolve/main/llama-2-7b.Q4_K_M.gguf",
  "size_bytes": 4200000000,
  "human_size": "4.2 GB"
}
```

#### POST `/api/gguf/download`

Start downloading a GGUF model.

**Request:**

```json
{
  "file_url": "https://huggingface.co/TheBloke/Llama-2-7B-GGUF/resolve/main/llama-2-7b.Q4_K_M.gguf",
  "filename": "llama-2-7b.Q4_K_M.gguf"
}
```

**Response:**

```json
{
  "task_id": "download_123456789",
  "status": "started",
  "websocket_url": "/ws/gguf/download/download_123456789"
}
```

#### WebSocket `/ws/gguf/download/{task_id}`

Monitor download progress.

**Events:**

```json
{
  "type": "progress",
  "downloaded_bytes": 1048576,
  "total_bytes": 4200000000,
  "percentage": 25.0,
  "speed_kbps": 1024
}
```

#### GET `/api/gguf/local`

List locally available GGUF models.

**Response:**

```json
{
  "models": [
    {
      "name": "llama-2-7b.Q4_K_M.gguf",
      "path": "/path/to/models/llama-2-7b.Q4_K_M.gguf",
      "size_bytes": 4200000000,
      "human_size": "4.2 GB",
      "modified": "2024-01-15T10:30:00Z"
    }
  ]
}
```

#### POST `/api/gguf/upload`

Upload a GGUF model file.

**Request:** `multipart/form-data` with file field `file`

**Response:**

```json
{
  "status": "success",
  "filename": "my-model.gguf",
  "size": 2100000000,
  "human_size": "2.1 GB",
  "message": "File uploaded successfully"
}
```

#### DELETE `/api/gguf/{model_name}`

Delete a GGUF model.

**Response:**

```json
{
  "status": "success",
  "message": "Model deleted successfully"
}
```

#### GET `/api/gguf/compatibility/{model_name}`

Check hardware compatibility for a GGUF model.

**Response:**

```json
{
  "compatible": true,
  "recommended_quantization": "Q4_K_M",
  "estimated_vram_mb": 4500,
  "available_vram_mb": 8192,
  "message": "Model compatible with current hardware"
}
```

### RAG (Retrieval-Augmented Generation)

#### POST `/api/rag/ingest`

Ingest documents for RAG.

**Request:** `multipart/form-data` with file field `file`

**Response:**

```json
{
  "document_id": "doc_123456789",
  "filename": "document.pdf",
  "chunks_created": 15,
  "message": "Document ingested successfully"
}
```

#### GET `/api/rag/search`

Search across ingested documents.

**Query Parameters:**

- `query`: Search query
- `limit`: Maximum results (default: 10)
- `conversation_id`: Optional conversation context

**Response:**

```json
{
  "results": [
    {
      "document_id": "doc_123456789",
      "chunk_id": "chunk_1",
      "content": "Relevant text from document...",
      "score": 0.85,
      "metadata": {
        "filename": "document.pdf",
        "page": 3
      }
    }
  ]
}
```

### File Upload & Processing

#### POST `/api/upload/image`

Upload and process an image.

**Request:** `multipart/form-data` with file field `file`

**Response:**

```json
{
  "file_id": "img_123456789",
  "filename": "image.png",
  "type": "image",
  "data": "data:image/png;base64,...",
  "metadata": {
    "width": 1024,
    "height": 768,
    "format": "PNG",
    "size_bytes": 524288
  },
  "ocr_text": "Text extracted from image..."
}
```

#### POST `/api/upload/document`

Upload and process a document.

**Request:** `multipart/form-data` with file field `file`

**Response:**

```json
{
  "file_id": "doc_123456789",
  "filename": "document.pdf",
  "type": "document",
  "text": "Extracted text from document...",
  "metadata": {
    "pages": 10,
    "size_bytes": 1048576,
    "truncated": false
  }
}
```

### Conversation Management

#### GET `/api/conversations`

List user conversations.

**Response:**

```json
{
  "conversations": [
    {
      "id": "conv_123456789",
      "title": "Discussion about AI",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:45:00Z",
      "message_count": 5
    }
  ]
}
```

#### GET `/api/conversations/{conversation_id}`

Get conversation messages.

**Response:**

```json
{
  "conversation": {
    "id": "conv_123456789",
    "title": "Discussion about AI",
    "messages": [
      {
        "id": "msg_1",
        "role": "user",
        "content": "Hello AI",
        "timestamp": "2024-01-15T10:30:00Z"
      },
      {
        "id": "msg_2",
        "role": "assistant",
        "content": "Hello! How can I help you today?",
        "timestamp": "2024-01-15T10:30:05Z"
      }
    ]
  }
}
```

#### DELETE `/api/conversations/{conversation_id}`

Delete a conversation.

**Response:**

```json
{
  "status": "success",
  "message": "Conversation deleted"
}
```

### System & Health

#### GET `/health`

Basic health check.

**Response:**

```json
{
  "status": "healthy",
  "auth": "jwt",
  "encryption": "fernet"
}
```

#### GET `/api/health`

Detailed system health.

**Response:**

```json
{
  "status": "ready",
  "message": "System Online",
  "progress": 100,
  "ready": true,
  "error": null
}
```

#### GET `/api/system/info`

System information.

**Response:**

```json
{
  "version": "0.1.0",
  "python_version": "3.10.12",
  "platform": "Linux",
  "hardware": {
    "backend": "cuda",
    "device": "NVIDIA RTX 4090",
    "vram_mb": 24576,
    "system_ram_mb": 32768
  },
  "database": {
    "type": "sqlite",
    "path": "./data/app.db"
  }
}
```

## WebSocket API

### Connection

```javascript
const ws = new WebSocket("ws://localhost:8000/ws/chat");
```

### Authentication

WebSocket connections automatically use the same authentication as HTTP requests (via cookies).

### Event Format

All WebSocket messages are JSON objects with a `type` field:

```json
{
  "type": "event_type",
  "session_id": "optional_session_id",
  "data": {},
  "timestamp": 1234567890
}
```

### Chat Events

#### `start_stream`

Start a new streaming session.

**Client → Server:**

```json
{
  "action": "start_stream",
  "data": {
    "message": "Hello AI",
    "provider": "openai",
    "model": "gpt-4o-mini",
    "deep_thinking_mode": true,
    "show_raw_response": false
  }
}
```

#### `cancel_session`

Cancel an active streaming session.

**Client → Server:**

```json
{
  "action": "cancel_session",
  "data": {
    "session_id": "session_123456789"
  }
}
```

#### `reasoning_step`

AI thinking step (server → client).

**Server → Client:**

```json
{
  "type": "reasoning_step",
  "step_index": 1,
  "step_type": "analysis",
  "title": "Analyzing the question",
  "content": "The user is asking about...",
  "metadata": {
    "confidence": 0.85
  }
}
```

#### `token_update`

New token in stream (server → client).

**Server → Client:**

```json
{
  "type": "token_update",
  "token": "Hello",
  "is_complete": false
}
```

#### `final_answer`

Complete response (server → client).

**Server → Client:**

```json
{
  "type": "final_answer",
  "content": "Hello! I'm an AI assistant...",
  "tokens_used": 45,
  "processing_time": 1.23
}
```

### GGUF Download Events

#### `progress`

Download progress update.

**Server → Client:**

```json
{
  "type": "progress",
  "task_id": "download_123456789",
  "downloaded_bytes": 1048576,
  "total_bytes": 4200000000,
  "percentage": 25.0,
  "speed_kbps": 1024,
  "eta_seconds": 120
}
```

#### `completed`

Download completed.

**Server → Client:**

```json
{
  "type": "completed",
  "task_id": "download_123456789",
  "filename": "llama-2-7b.Q4_K_M.gguf",
  "size_bytes": 4200000000,
  "message": "Download completed successfully"
}
```

#### `error`

Download error.

**Server → Client:**

```json
{
  "type": "error",
  "task_id": "download_123456789",
  "error": "Network error",
  "message": "Failed to download file"
}
```

## Error Handling

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong",
  "error_code": "ERROR_CODE",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Common Error Codes

- `AUTH_REQUIRED`: Authentication required
- `INVALID_TOKEN`: Invalid or expired token
- `PERMISSION_DENIED`: Insufficient permissions
- `VALIDATION_ERROR`: Request validation failed
- `MODEL_NOT_FOUND`: Requested model not available
- `RATE_LIMITED`: Rate limit exceeded
- `INTERNAL_ERROR`: Internal server error

### HTTP Status Codes

- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Authentication required or failed
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

## Rate Limiting

API endpoints are rate-limited to prevent abuse:

- **Authentication endpoints**: 10 requests per minute
- **Chat endpoints**: 60 requests per minute
- **File uploads**: 5 requests per minute
- **GGUF downloads**: 2 concurrent downloads per user

Rate limit headers are included in responses:

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1705312800
```

## Pagination

List endpoints support pagination:

**Query Parameters:**

- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20, max: 100)

**Response Headers:**

```http
X-Total-Count: 150
X-Total-Pages: 8
X-Current-Page: 1
X-Per-Page: 20
```

## Examples

### Complete Chat Example

```bash
# 1. Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'

# 2. Send chat message (uses cookies for auth)
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain quantum computing",
    "provider": "openai",
    "model": "gpt-4o-mini"
  }'
```

### GGUF Download Example

```bash
# Start download
curl -X POST http://localhost:8000/api/gguf/download \
  -H "Content-Type: application/json" \
  -d '{
    "file_url": "https://huggingface.co/TheBloke/Llama-2-7B-GGUF/resolve/main/llama-2-7b.Q4_K_M.gguf"
  }'

# Check local models
curl http://localhost:8000/api/gguf/local
```

## SDKs & Client Libraries

### Python

```python
import requests

class LMWebUIClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()

    def chat(self, message, provider="openai", model="gpt-4o-mini"):
        response = self.session.post(
            f"{self.base_url}/api/chat",
            json={
                "message": message,
                "provider": provider,
                "model": model
            }
        )
        return response.json()
```

### JavaScript/TypeScript

```typescript
class LMWebUIClient {
  constructor(private baseUrl: string = 'http://localhost:8000') {}

  async chat(message: string, provider = 'openai', model = 'gpt-4o-mini') {
    const response = await fetch(`${this.baseUrl}/api/chat`, {
      method: '
```
