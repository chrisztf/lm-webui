# Deployment Guide

This guide covers how to deploy the LM WebUI application using Docker Compose, with instructions for enabling hardware acceleration (NVIDIA CUDA, Apple Silicon).

## Prerequisites

- **Docker**: [Install Docker Desktop](https://www.docker.com/products/docker-desktop)
- **Docker Compose**: Included with Docker Desktop.
- **NVIDIA GPU Users**: [Install NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) for CUDA support.

## 🚀 One-Line Installation (Recommended)

The easiest way to install and run LM WebUI is with our one-line installation script:

```bash
curl -sSL https://raw.githubusercontent.com/lm-webui/lm-webui/main/install.sh | bash
```

This script will:

1. Check for prerequisites (Docker, Docker Compose)
2. Clone the repository (if needed)
3. Set up environment configuration
4. Build and start the Docker containers
5. Provide access instructions

## 🛠️ Manual Installation

If you prefer manual installation:

1.  **Clone the repository**:

    ```bash
    git clone https://github.com/lm-webui/lm-webui.git
    cd lm-webui
    ```

2.  **Start the application**:

    ```bash
    docker-compose up --build
    ```

3.  **Access the application**:
    - **Frontend**: http://localhost:7070
    - **Backend API Docs**: http://localhost:7070/docs

## ⚙️ Configuration

### Environment Variables

The installation script creates a `.env` file with template configuration. You can configure the backend by editing this file or setting environment variables in `docker-compose.yml`.

**Key Variables:**

- `OPENAI_API_KEY`: API Key for OpenAI.
- `ANTHROPIC_API_KEY`: API Key for Claude.
- `GEMINI_API_KEY`: API Key for Google Gemini.
- `XAI_API_KEY`: API Key for Grok.
- `DEEPSEEK_API_KEY`: API Key for DeepSeek.
- `LOCAL_MODELS_DIR`: Path to local GGUF models (default: `./backend/models`)
- `PORT`: Application port (default: `7070`)
- `HOST`: Bind address (default: `0.0.0.0`)

### Adding Local Models

To use local GGUF models:

1.  Download `.gguf` models (e.g., from [Hugging Face](https://huggingface.co/TheBloke)).
2.  Place them in the `backend/models/` directory.
3.  Restart the container or refresh models in the UI.

The `backend/models` directory is mounted to the container, so new models are detected automatically.

## 🏎️ Hardware Acceleration

The application supports hardware acceleration for faster local inference.

### NVIDIA GPU (CUDA)

1.  **Ensure Prerequisites**: Install Docker and the NVIDIA Container Toolkit.
2.  **Docker Compose**: The `docker-compose.yml` is already configured for GPU passthrough:
    ```yaml
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    ```
3.  **Build with CUDA Support**:
    Modify `docker-compose.yml` to set the build argument:
    ```yaml
    backend:
      build:
        args:
          CMAKE_ARGS: "-DGGML_CUDA=on"
    ```
4.  **Run**: `docker-compose up --build`

### Apple Silicon (Metal/MPS)

Docker on macOS has limitations with direct GPU passthrough. However, the backend is capable of using Metal (MPS) when running natively.

**For Docker on macOS:**

- The container runs in a Linux VM. Metal acceleration is **not currently supported** inside standard Docker containers on macOS.
- The application will fall back to CPU inference, which is reasonably fast on M-series chips for smaller models (checking `backend/app/hardware/detection.py`).

**For Native Performance (Recommended for Mac):**
If you need maximum performance on Apple Silicon, run the backend natively:

1.  **Install Backend**:
    ```bash
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    CMAKE_ARGS="-DGGML_METAL=on" pip install --force-reinstall --no-cache-dir llama-cpp-python
    pip install -r requirements.txt
    python -m app.main
    ```
2.  **Run Frontend**:
    ```bash
    cd frontend
    npm install
    npm run dev
    ```

## 💾 Persistence

The following data is persisted using Docker volumes and local directories:

- **Database & Vector Store**: Docker volume `lm-webui_app_data` (mounted at `/backend/data` in container)
- **User Media**: Docker volume `lm-webui_app_media` (mounted at `/backend/media` in container)
- **Local Models**: `./backend/models/` on host (mounted to `/backend/data/models` in container)
- **RAG Models**: `./backend/rag/` (RAG model files)
- **Build Cache**: Docker volume for JIT compilation speedups
- **Configuration**: `./backend/config.yaml` on host (mounted to `/backend/config.yaml` in container)
- **Secrets**: `./backend/.secrets/` on host (mounted to `/backend/.secrets` in container)

This ensures that your conversation history, knowledge graph, uploaded files, and downloaded models survive container restarts.

**Accessing Docker Volume Data:**

To access data stored in Docker volumes:

```bash
# List volumes
docker volume ls

# Inspect a volume
docker volume inspect lm-webui_app_data

# Backup a volume
docker run --rm -v lm-webui_app_data:/data -v $(pwd):/backup alpine tar czf /backup/backup.tar.gz -C /data .

# Restore to a volume
docker run --rm -v lm-webui_app_data:/data -v $(pwd):/backup alpine sh -c "cd /data && tar xzf /backup/backup.tar.gz --strip 1"
```

**Directory Structure in Container:**

```
/backend/data/
├── sql_db/        # SQlite database
├── qdrant_db/     # Vector database for RAG
└── memory/        # Knowledge graph database

/backend/media/
├── uploads/       # User uploaded files
├── thumbnails/    # Generated thumbnails
└── generated/     # AI-generated content
    ├── images/
    ├── documents/
    └── exports/

/backend/rag/
├── embed/         # embedding model
├── ocr/           # ocr model
├── rerank/        # rerank model
└── vision/        # vision model

/backend/data/models/  # downloaded local GGUF models directory (mounted from host ./backend/models/)
```

## 🛠️ Troubleshooting

### Common Issues

- **Port Conflicts**: If port `7070` is in use, modify the `ports` mapping in `docker-compose.yml`:

  ```yaml
  ports:
    - "7070:8000" # Change 7070 to your preferred port
  ```

- **Permission Issues**: If you encounter permission errors with volumes on Linux:

  ```bash
  sudo chown -R $USER:$USER ./backend/data ./backend/media ./backend/models
  ```

- **Docker Build Failures**: If the build fails due to network issues:

  ```bash
  docker system prune -a  # Clean Docker cache
  docker-compose build --no-cache  # Rebuild without cache
  ```

- **GPU Not Detected**: For NVIDIA GPU users:

  ```bash
  # Check NVIDIA Container Toolkit is installed
  nvidia-smi
  docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi
  ```

- **Application Not Starting**: Check logs:
  ```bash
  docker-compose logs -f
  ```

### Installation Script Issues

If the one-line installation fails:

1. **Run manually step by step**:

   ```bash
   git clone https://github.com/lm-webui/lm-webui.git
   cd lm-webui
   chmod +x install.sh
   ./install.sh
   ```

2. **Check Docker is running**:

   ```bash
   docker info
   ```

3. **Verify internet connection**:
   ```bash
   curl -I https://github.com
   ```
