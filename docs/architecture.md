# 🏗️ System Architecture

## 🔭 High-Level Overview

The application follows a modern decoupled architecture, composed of a reactive **Single Page Application (SPA)** frontend and a high-performance **FastAPI** backend. The system is designed for local LLM inference, RAG (Retrieval-Augmented Generation), and multimodal interaction, emphasizing data privacy and hardware acceleration.

---

## 🖥️ Frontend Architecture

Built with **React 18** and **TypeScript**, leveraging **Vite** for build performance. The frontend adopts a Feature-First architecture to maintain scalability.

### 🧩 Core Stack

- **Framework:** React + TypeScript + Vite
- **Styling:** Tailwind CSS + [shadcn/ui](https://ui.shadcn.com/)
- **State Management:**
  - **Global State:** `Zustand` (High-frequency updates like chat streams)
  - **App State:** React Context (Auth, Theme)
- **Network:** Axios (REST) + Native WebSockets (Real-time streaming)

### 📂 Structural Organization (`frontend/src`)

| Layer        | Directory     | Description                                                                                                   |
| ------------ | ------------- | ------------------------------------------------------------------------------------------------------------- |
| **Features** | `features/`   | Domain silos (Chat, Documents, Images, Models) containing dedicated hooks, services, and types.               |
| **UI Kit**   | `components/` | Atomic design components (`ui/`) and complex functional widgets (`chat/`, `reasoning/`).                      |
| **Store**    | `store/`      | Reactive state stores for managing chat sessions, reasoning steps, and context.                               |
| **Services** | `services/`   | WebSocket clients (`conversationWebSocketService`, `reasoningWebSocketService`) handling real-time data flow. |

---

## ⚡ Backend Architecture

Powered by **Python FastAPI**, the backend employs a **Modular Monolith** pattern. It separates core domain logic from API routing, utilizing a specialized hardware abstraction layer for optimized local inference.

### 🏗️ Architectural Layers

#### 1. Interface Layer (`routes/`)

The entry point for all external requests.

- **REST APIs:** Standard endpoints for resource management (Uploads, Settings, Models).
- **WebSockets:** Dedicated channels for low-latency token streaming and reasoning updates.

#### 2. Domain Engines

specialized modules encapsulating complex logic:

- **🧠 Memory Engine (`memory/`)**:
  - Context Assembler: Dynamic context window management.
  - Knowledge Graph: Structured information retention (`kg_manager`).
  - Summarization: Long-term memory compression.
- **📚 RAG Engine (`rag/`)**:
  - Hybrid Search: Combining semantic (Vector) and keyword search.
  - Ingestion Pipeline: OCR, Chunking, and Embedding.
  - Vector Store: Local vector database management.
- **🌊 Streaming Engine (`streaming/`)**:
  - Event System: Pub/sub model for decoupling inference from network responses.
  - Reasoning Parser: Real-time parsing of chain-of-thought tokens.

#### 3. Service Layer (`services/`)

Orchestrates business processes and external integrations:

- **Model Management:** GGUF resolution, downloading, and validation.
- **Multimodal:** Image generation and vision services.
- **Process Manager:** Handling background tasks and optimizations.

#### 4. Hardware Abstraction Layer (`hardware/`)

A cross-cutting concern that optimizes runtime performance:

- **Detection:** Auto-identifies execution providers (CUDA, ROCm, Metal, CPU).
- **Management:** Resource allocation and offloading strategies.

### 💾 Data Persistence

- **Relational:** SQLite with connection pooling (`database/`) for structured data (Chat history, users).
- **Vector:** Local embeddings storage for document retrieval.
- **File System:** Managed storage for local LLMs, uploads, and generated artifacts.

---

## 🔄 Critical Workflows

### 🗣️ Chat Inference Pipeline

1.  **Request:** User sends prompt via WebSocket.
2.  **Contextualization:** `Memory Engine` retrieves relevant history and RAG documents.
3.  **Optimization:** `Hardware Layer` configures the model loader.
4.  **Generation:** Model generates tokens; `Streaming Engine` captures and emits events.
5.  **Response:** Frontend `Zustand` store updates UI in real-time.
6.  **Persistence:** `ChatController` saves assistant messages to database after streaming completes.

### 📄 RAG Ingestion Pipeline

1.  **Upload:** File received at `routes/upload`.
2.  **Processing:** `rag/processor` extracts text (OCR if needed).
3.  **Indexing:** `rag/embedder` converts text to vectors.
4.  **Storage:** Vectors saved to local store; Metadata to SQLite.

---

## 🏗️ DRY Implementation & Code Quality

### Backend DRY Improvements

1. **Standardized Error Handling**: Unified error response format across all endpoints
2. **Consolidated Upload Endpoints**: Single upload service handling multiple file types
3. **Removed Dormant Tasks**: Cleaned up unused background tasks and services
4. **Chat Service Abstraction**: Unified chat logic with proper separation of concerns
5. **Standardized Provider Interfaces**: Consistent interfaces for model providers
6. **Updated Configuration Management**: Environment-based configuration with validation

### Frontend DRY Improvements

1. **Unified Type System**: Consolidated TypeScript interfaces in `frontend/src/types/core/`
2. **Store Architecture Refactoring**: Slice-based Zustand stores with unified patterns
3. **Service Layer Standardization**: Consistent API service patterns
4. **Component Consolidation**: Reusable UI components with proper prop interfaces

### Streaming Pipeline Fixes

- **Fixed WebSocket Streaming**: Resolved "Model is still thinking..." status issue
- **Message Persistence**: Assistant messages now properly saved to database
- **Event System**: Proper `type: "complete"` events for frontend synchronization

---

## 📁 Repository Structure (Open-Source Ready)

```
lm-webui/
├── 📁 backend/                    # FastAPI backend
│   ├── app/                      # Application code
│   │   ├── routes/              # API endpoints
│   │   ├── services/            # Business logic
│   │   ├── rag/                 # RAG engine
│   │   ├── hardware/            # Hardware abstraction
│   │   └── database/            # Data persistence
│   └── tests/                   # Backend tests
├── 📁 frontend/                  # React + TypeScript frontend
│   ├── src/
│   │   ├── components/          # UI components
│   │   ├── features/            # Feature modules
│   │   ├── store/              # State management
│   │   ├── services/           # API services
│   │   └── types/core/         # Unified type definitions
│   └── tests/                  # Frontend tests
├── 📁 docs/                     # Documentation
│   ├── implementation/         # Implementation details
│   ├── prompts/               # Prompt templates
│   └── testing/               # Test documentation
├── 📁 scripts/                 # Utility scripts
│   ├── debug/                 # Debug scripts
│   └── tests/                 # Test utilities
├── 📁 examples/                # Example configurations
│   └── samples/               # Sample files
├── 📁 .github/                 # GitHub configuration
│   ├── workflows/             # CI/CD pipelines
│   ├── ISSUE_TEMPLATE/        # Issue templates
│   └── instructions/          # Development instructions
├── 📄 LICENSE                  # MIT License
├── 📄 CONTRIBUTING.md          # Contribution guidelines
├── 📄 README.md                # Project documentation
├── 📄 architecture.md          # Architecture documentation
├── 📄 DEPLOYMENT.md            # Deployment instructions
├── 📄 docker-compose.yml       # Docker Compose configuration
├── 📄 Dockerfile               # Docker build configuration
├── 📄 install.sh               # One-line installation script
└── 📄 cleanup_repository.sh    # Repository organization script
```

---

## 🚀 Deployment & Operations

### Single-Command Deployment

```bash
# One-line installation
curl -sSL https://raw.githubusercontent.com/lm-webui/lm-webui/main/install.sh | bash

# Or using the local script
./install.sh
```

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# With GPU support (NVIDIA)
docker-compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

### Development Environment

```bash
# Frontend development
cd frontend
npm install
npm run dev

# Backend development
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

---

## 🧪 Testing Strategy

### Backend Testing

- **Unit Tests**: Pytest for individual components
- **Integration Tests**: End-to-end API testing
- **WebSocket Tests**: Real-time communication testing
- **Hardware Tests**: GPU/CPU acceleration validation

### Frontend Testing

- **Component Tests**: React component testing
- **Store Tests**: Zustand store testing
- **Integration Tests**: API integration testing
- **E2E Tests**: Full user workflow testing

### CI/CD Pipeline

- **GitHub Actions**: Automated testing on push/PR
- **Docker Build Validation**: Container build testing
- **Code Coverage**: >80% test coverage target
- **Security Scanning**: Snyk integration for vulnerability detection

---

## 🔒 Security & Compliance

### Data Privacy

- **Local-First Design**: Data remains on user's infrastructure
- **Encryption**: Secure storage for sensitive data
- **Access Control**: Role-based authentication (planned)

### Security Features

- **Input Validation**: Sanitization of all user inputs
- **Rate Limiting**: Protection against abuse
- **Audit Logging**: Comprehensive activity tracking
- **Vulnerability Scanning**: Regular dependency updates

---

## 📈 Performance Characteristics

### Backend Performance

- **Response Time**: <100ms for API endpoints
- **WebSocket Latency**: <50ms for real-time updates
- **Model Loading**: Optimized GGUF loading with hardware detection
- **Memory Management**: Efficient context window handling

### Frontend Performance

- **Bundle Size**: <2MB initial load
- **Time to Interactive**: <3 seconds
- **WebSocket Reconnection**: Automatic reconnection with state recovery
- **Offline Support**: Partial offline functionality

---

## 🤝 Community & Contribution

### Open-Source Ready

- **MIT License**: Permissive open-source licensing
- **Comprehensive Documentation**: Complete setup and usage guides
- **Issue Templates**: Standardized bug reports and feature requests
- **Contribution Guidelines**: Clear process for community contributions

### Development Workflow

- **Conventional Commits**: Standardized commit messages
- **Code Review**: Required for all changes
- **Testing Requirements**: Comprehensive test coverage
- **Documentation Updates**: Required for feature changes
