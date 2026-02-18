# Installation

This guide covers all installation methods for LM WebUI, from simple Docker setups to advanced production deployments.

## Installation Methods

### Method 1: Docker (Recommended)

**Best for**: Quick setup, testing, and production deployment

```bash
# Clone the repository
git clone https://github.com/lm-webui/lm-webui.git
cd lm-webui

# Start with Docker Compose (includes everything)
docker-compose up

# Or build and run individually
docker build -t lm-webui-backend ./backend
docker build -t lm-webui-frontend ./frontend
docker run -p 8000:8000 lm-webui-backend
docker run -p 5178:5178 lm-webui-frontend
```

### Method 2: Manual Installation

**Best for**: Development, customization, and debugging

```bash
# 1. Clone repository
git clone https://github.com/lm-webui/lm-webui.git
cd lm-webui

# 2. Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# For development with testing
pip install -r requirements-test.txt

# 3. Frontend setup
cd ../frontend
npm install

# For production build
npm run build
```

### Method 3: Production Deployment

**Best for**: Self-hosted production environments

See the [Deployment Guide](./deployment.md) for detailed production setup instructions.

## System Requirements

### Minimum Requirements

- **CPU**: 2+ cores
- **RAM**: 4GB
- **Storage**: 10GB free space
- **OS**: Linux, macOS, or Windows (WSL2 recommended for Windows)

### Recommended for Local Models

- **CPU**: 4+ cores
- **RAM**: 8GB+ (16GB for larger models)
- **Storage**: 20GB+ for model storage
- **GPU**: NVIDIA/AMD/Apple Silicon for acceleration (optional but recommended)

### Production Requirements

- **CPU**: 4+ cores
- **RAM**: 16GB+
- **Storage**: 50GB+ (for models and data)
- **GPU**: Dedicated GPU with 8GB+ VRAM for optimal performance
- **Database**: PostgreSQL for multi-user environments

## Prerequisites

### 1. Python (Backend)

- **Version**: Python 3.9 or higher
- **Package Manager**: pip

**Check your Python version:**

```bash
python --version
python3 --version
```

**Install Python (if needed):**

- **Ubuntu/Debian**: `sudo apt update && sudo apt install python3 python3-pip python3-venv`
- **macOS**: `brew install python`
- **Windows**: Download from [python.org](https://python.org)

### 2. Node.js (Frontend)

- **Version**: Node.js 16 or higher
- **Package Manager**: npm or yarn

**Check your Node.js version:**

```bash
node --version
npm --version
```

**Install Node.js (if needed):**

- **Ubuntu/Debian**: `curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash - && sudo apt install -y nodejs`
- **macOS**: `brew install node`
- **Windows**: Download from [nodejs.org](https://nodejs.org)

### 3. Database

- **Development**: SQLite (included, no setup needed)
- **Production**: PostgreSQL recommended

**Install PostgreSQL (optional for production):**

```bash
# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib

# macOS
brew install postgresql

# Windows
# Download from https://www.postgresql.org/download/windows/
```

### 4. Docker (Optional but Recommended)

- **Docker Engine**: For containerization
- **Docker Compose**: For multi-container setup

**Install Docker:**

- Follow instructions at [docker.com](https://docs.docker.com/get-docker/)

## Step-by-Step Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/lm-webui/lm-webui.git
cd lm-webui
```

### Step 2: Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p data .secrets

# Initialize database
python -c "from app.database import init_db; init_db()"

# Create JWT secret (if not exists)
python -c "from app.security.auth.core import ensure_jwt_secret; ensure_jwt_secret()"
```

### Step 3: Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install

# Create environment file
echo "VITE_BACKEND_URL=http://localhost:8000" > .env.local
```

### Step 4: Configuration

#### Backend Configuration

Create `backend/.env`:

```bash
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
DATABASE_URL=sqlite:///./data/app.db
# Optional: Add API keys for cloud providers
# OPENAI_API_KEY=your-key-here
# ANTHROPIC_API_KEY=your-key-here
```

Create `backend/config.yaml` (optional for advanced config):

```yaml
server:
  host: "0.0.0.0"
  port: 8000
  reload: true

database:
  url: "sqlite:///./data/app.db"
  echo: false

security:
  jwt_secret_path: ".secrets/jwt_secret"
  allowed_origins:
    - "http://localhost:5178"
    - "http://localhost:8000"

llm:
  default_model: "gpt-4o-mini"
  temperature: 0.7
```

#### Frontend Configuration

Create `frontend/.env.local`:

```bash
VITE_BACKEND_URL=http://localhost:8000
VITE_API_TIMEOUT=30000
VITE_WEBSOCKET_RECONNECT_ATTEMPTS=3
```

### Step 5: Start Services

#### Option A: Development Mode (Recommended for Development)

```bash
# Terminal 1: Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Frontend
cd frontend
npm run dev
```

#### Option B: Production Mode

```bash
# Build frontend
cd frontend
npm run build

# Start backend (serves built frontend)
cd ../backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### Option C: Docker Compose

```bash
# From project root
docker-compose up
```

### Step 6: Verify Installation

1. **Check backend health:**

   ```bash
   curl http://localhost:8000/health
   # Should return: {"status": "healthy", "auth": "jwt", "encryption": "fernet"}
   ```

2. **Check frontend:**
   Open `http://localhost:5178` in your browser

3. **Create an account:**
   - Open the application
   - Click "Register"
   - Enter email and password
   - You should be logged in automatically

## Platform-Specific Instructions

### Linux

```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nodejs npm git

# Proceed with standard installation
```

### macOS

```bash
# Install Homebrew if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python node git

# Proceed with standard installation
```

### Windows (WSL2 Recommended)

```bash
# 1. Install WSL2 (Windows Subsystem for Linux)
# Follow: https://docs.microsoft.com/en-us/windows/wsl/install

# 2. Install Ubuntu from Microsoft Store

# 3. Open Ubuntu terminal and proceed with Linux instructions
```

### Windows (Native)

```bash
# 1. Install Python from python.org
# 2. Install Node.js from nodejs.org
# 3. Install Git from git-scm.com

# Use PowerShell or Command Prompt
# Note: Use `python` instead of `python3`, `venv\Scripts\activate` instead of `source venv/bin/activate`
```

## Post-Installation Setup

### 1. Download GGUF Models

1. Open the application
2. Go to Settings → Models
3. Click "Download Model"
4. Enter a HuggingFace URL or search for models
5. Recommended starter model: `TheBloke/Llama-2-7B-GGUF`

### 2. Configure API Keys (Optional)

1. Go to Settings → API Keys
2. Add keys for:
   - OpenAI (for GPT models)
   - Anthropic (for Claude)
   - Google (for Gemini)
   - Other supported providers

### 3. Test the System

```bash
# Run backend tests
cd backend
pytest

# Run frontend tests
cd ../frontend
npm test
```

## Troubleshooting Installation

### Common Issues

#### "Python not found"

```bash
# Check if Python is installed
python3 --version

# If not, install it
# Ubuntu: sudo apt install python3
# macOS: brew install python
# Windows: Download from python.org
```

#### "npm not found"

```bash
# Check if Node.js is installed
node --version

# If not, install it
# Ubuntu: sudo apt install nodejs npm
# macOS: brew install node
# Windows: Download from nodejs.org
```

#### "Port already in use"

```bash
# Find process using port 8000 or 5178
# Linux/macOS:
lsof -ti:8000 | xargs kill -9
lsof -ti:5178 | xargs kill -9

# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

#### "Database errors"

```bash
# Delete and recreate database
rm -f backend/data/app.db
cd backend
python -c "from app.database import init_db; init_db()"
```

#### "Module not found" errors

```bash
# Reinstall dependencies
cd backend
pip install -r requirements.txt

cd ../frontend
npm install
```

## Next Steps

- Read the [Getting Started](./getting-started.md) guide for first-time usage
- Explore [Features](./features.md) to learn about all capabilities
- Check [Deployment](./deployment.md) for production setup
- Review [API Reference](./api-reference.md) for integration options

## Getting Help

If you encounter issues:

1. Check the [Troubleshooting](./troubleshooting.md) guide
2. Search [GitHub Issues](https://github.com/lm-webui/lm-webui/issues)
3. Ask in [GitHub Discussions](https://github.com/lm-webui/lm-webui/discussions)
4. Review the documentation for your specific issue
