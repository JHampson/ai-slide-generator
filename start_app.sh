#!/bin/bash

# AI Slide Generator - Start Script
# Starts both backend and frontend servers

set -e

echo "🚀 Starting AI Slide Generator..."
echo ""

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Load environment variables from .env file
if [ -f .env ]; then
    echo -e "${BLUE}🔧 Loading environment variables from .env...${NC}"
    # Export variables safely (handles values with spaces) - macOS compatible
    set -a  # automatically export all variables
    source .env
    set +a  # disable automatic export
    echo -e "${GREEN}✅ Environment variables loaded${NC}"
else
    echo -e "${RED}❌ .env file not found${NC}"
    echo ""
    echo "Please create .env file:"
    echo -e "  ${BLUE}cp .env.example .env${NC}"
    echo -e "  ${BLUE}nano .env${NC}  # Set DATABRICKS_HOST and DATABRICKS_TOKEN"
    echo ""
    exit 1
fi

# Validate required environment variables
if [ -z "$DATABRICKS_HOST" ] || [ -z "$DATABRICKS_TOKEN" ]; then
    echo -e "${RED}❌ Missing required environment variables${NC}"
    echo ""
    echo "Please ensure .env file contains:"
    echo "  - DATABRICKS_HOST=https://your-workspace.cloud.databricks.com"
    echo "  - DATABRICKS_TOKEN=your-token-here"
    echo ""
    exit 1
fi

# Check if .venv exists
if [ ! -d ".venv" ]; then
    echo -e "${RED}❌ Virtual environment not found${NC}"
    echo ""
    echo "Please run the setup first:"
    echo -e "  ${BLUE}./quickstart/setup.sh${NC}         # Full setup"
    echo "  or"
    echo -e "  ${BLUE}./quickstart/create_python_environment.sh${NC}  # Just Python env"
    echo ""
    exit 1
fi

# Activate virtual environment
echo -e "${BLUE}🔧 Activating virtual environment...${NC}"
source .venv/bin/activate

# Verify critical dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo -e "${RED}❌ Dependencies not properly installed${NC}"
    echo ""
    echo "Please run: ${BLUE}./quickstart/create_python_environment.sh${NC}"
    echo ""
    exit 1
fi
echo -e "${GREEN}✅ Dependencies verified${NC}"

# Set environment variables for development
export ENVIRONMENT="development"
export DEV_USER_ID="dev@local.dev"
export DEV_USER_EMAIL="dev@local.dev"
export DEV_USERNAME="Dev User"

# Check if frontend directory exists
if [ ! -d "frontend" ]; then
    echo -e "${YELLOW}⚠️  Frontend directory not found. Skipping frontend startup.${NC}"
    echo -e "${YELLOW}    Run the frontend setup first.${NC}"
    SKIP_FRONTEND=true
else
    SKIP_FRONTEND=false
    
    # Check if frontend dependencies are installed
    if [ ! -d "frontend/node_modules" ]; then
        echo -e "${YELLOW}⚠️  Frontend dependencies not installed. Installing...${NC}"
        cd frontend
        npm install
        cd ..
        echo -e "${GREEN}✅ Frontend dependencies installed${NC}"
    fi
fi

# Create log directory
mkdir -p logs

# Ensure database tables exist (safe to run multiple times)
echo -e "${BLUE}🔧 Ensuring database tables exist...${NC}"
python -c "
# Import database first (no circular import issues)
from src.core.database import Base, get_engine, init_db
# Then import models to register them with Base.metadata
from src.database.models.ai_infra import ConfigAIInfra
from src.database.models.genie_space import ConfigGenieSpace
from src.database.models.profile import ConfigProfile
from src.database.models.prompts import ConfigPrompts
from src.database.models.profile_tool import ProfileTool
from src.database.models.tool_library import ToolLibrary
from src.database.models.slide_deck_prompt import SlideDeckPromptLibrary
from src.database.models.slide_style_library import SlideStyleLibrary
from src.database.models.session import UserSession, SessionMessage, SessionSlideDeck, ChatRequest
from src.database.models.history import ConfigHistory
# Now create all tables
init_db()
print('Database tables ready')
"
echo -e "${GREEN}✅ Database ready${NC}"

# Start backend in background
echo -e "${BLUE}🔧 Starting backend on port 8000...${NC}"
nohup uvicorn src.api.main:app --reload --port 8000 > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > logs/backend.pid
echo -e "${GREEN}✅ Backend started (PID: $BACKEND_PID)${NC}"

# Wait for backend to be ready
echo -e "${BLUE}⏳ Waiting for backend to be ready...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend is ready${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${YELLOW}⚠️  Backend health check timeout. Check logs/backend.log${NC}"
    fi
    sleep 1
done

# Start frontend in background (if exists)
if [ "$SKIP_FRONTEND" = false ]; then
    echo -e "${BLUE}🔧 Starting frontend on port 3000...${NC}"
    cd frontend
    nohup npm run dev > ../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > ../logs/frontend.pid
    cd ..
    echo -e "${GREEN}✅ Frontend started (PID: $FRONTEND_PID)${NC}"
fi

echo ""
echo -e "${GREEN}✨ AI Slide Generator is running!${NC}"
echo ""
echo "📍 URLs:"
if [ "$SKIP_FRONTEND" = false ]; then
    echo "   Frontend: http://localhost:3000"
fi
echo "   Backend:  http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "📋 Process IDs:"
echo "   Backend:  $BACKEND_PID"
if [ "$SKIP_FRONTEND" = false ]; then
    echo "   Frontend: $FRONTEND_PID"
fi
echo ""
echo "📝 Logs:"
echo "   Backend:  tail -f logs/backend.log"
if [ "$SKIP_FRONTEND" = false ]; then
    echo "   Frontend: tail -f logs/frontend.log"
fi
echo ""
echo "🛑 To stop: ./stop_app.sh"
echo ""

