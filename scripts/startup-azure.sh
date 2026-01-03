#!/bin/bash
# Azure App Service startup script for WindX Product Configurator
# Deployment Version: v1.0.1
# Last Updated: 2026-01-03

set -e  # Exit on error

echo "=========================================="
echo "🪟 WindX Product Configurator - Azure Deployment"
echo "=========================================="
echo ""

# System Information
echo "📋 System Information:"
echo "   Hostname: $(hostname)"
echo "   Date: $(date)"
echo "   User: $(whoami)"
echo "   Working Directory: $(pwd)"
echo "   Python Path: $(which python3 || which python)"
echo ""

# Application Metadata
echo "🏷️  Application Metadata:"
APP_VERSION="1.0.0"
SCRIPT_VERSION="v1.0.1"

# Try to read version from VERSION file
if [ -f "VERSION" ]; then
    APP_VERSION=$(cat VERSION 2>/dev/null || echo "1.0.0")
    echo "   📄 Version read from VERSION file: ${APP_VERSION}"
fi

echo "   Name: WindX Product Configurator"
echo "   App Version: ${APP_VERSION}"
echo "   Deployment Script Version: ${SCRIPT_VERSION}"
echo "   Description: Automated product configurator for custom manufacturing"
echo "   Author: alaamer12 <ahmedmuhmmed239@gmail.com>"
echo "   License: MIT"
echo "   Repository: https://github.com/alaamer12/Windx"
echo ""

# Python Information
echo "🐍 Python Environment:"
python3 --version || python --version
echo "   Python Path: $(which python3 || which python)"
echo "   Pip Version: $(pip3 --version || pip --version)"
echo ""

# Git Information & Deployment Tracking
echo "🚀 Deployment Information:"
if [ -d .git ]; then
    COMMIT_HASH=$(git log -1 --pretty=format:'%H' 2>/dev/null || echo 'N/A')
    SHORT_HASH=$(git log -1 --pretty=format:'%h' 2>/dev/null || echo 'N/A')
    COMMIT_MESSAGE=$(git log -1 --pretty=format:'%s' 2>/dev/null || echo 'N/A')
    COMMIT_DATE=$(git log -1 --pretty=format:'%ci' 2>/dev/null || echo 'N/A')
    COMMIT_AUTHOR=$(git log -1 --pretty=format:'%an' 2>/dev/null || echo 'N/A')
    BRANCH_NAME=$(git branch --show-current 2>/dev/null || git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'N/A')
    
    echo "   📝 Last Commit Hash: ${COMMIT_HASH}"
    echo "   🔗 Short Hash: ${SHORT_HASH}"
    echo "   💬 Commit Message: ${COMMIT_MESSAGE}"
    echo "   📅 Commit Date: ${COMMIT_DATE}"
    echo "   👤 Commit Author: ${COMMIT_AUTHOR}"
    echo "   🌿 Branch: ${BRANCH_NAME}"
    
    # Create deployment info file for runtime access
    cat > /tmp/deployment-info.json << EOF
{
    "deployment_time": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "app_version": "${APP_VERSION}",
    "commit_hash": "${COMMIT_HASH}",
    "short_hash": "${SHORT_HASH}",
    "commit_message": "${COMMIT_MESSAGE}",
    "commit_date": "${COMMIT_DATE}",
    "commit_author": "${COMMIT_AUTHOR}",
    "branch": "${BRANCH_NAME}",
    "script_version": "${SCRIPT_VERSION}"
}
EOF
    echo "   📄 Deployment info saved to /tmp/deployment-info.json"
else
    echo "   ⚠️  Git: Not a git repository (deployed from archive)"
    echo "   📦 Deployment Method: Archive/ZIP upload"
    
    # Create basic deployment info
    cat > /tmp/deployment-info.json << EOF
{
    "deployment_time": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "app_version": "${APP_VERSION}",
    "commit_hash": "N/A",
    "short_hash": "N/A", 
    "commit_message": "Deployed from archive",
    "commit_date": "N/A",
    "commit_author": "N/A",
    "branch": "N/A",
    "script_version": "${SCRIPT_VERSION}",
    "deployment_method": "archive"
}
EOF
fi
echo ""

# Disk Space
echo "💾 Disk Space:"
df -h / | tail -1 | awk '{print "   Total: "$2" | Used: "$3" | Available: "$4" | Usage: "$5}'
echo ""

# Install UV package manager
echo "📦 Installing UV..."
if ! command -v uv &> /dev/null; then
    pip3 install --upgrade pip || pip install --upgrade pip
    pip3 install uv || pip install uv
    echo "✅ UV installed"
else
    echo "✅ UV already installed"
    uv --version
fi
echo ""

# Install dependencies using UV
echo "📦 Installing Dependencies..."
cd /home/site/wwwroot

# Check if pyproject.toml exists
if [ ! -f "pyproject.toml" ]; then
    echo "❌ pyproject.toml not found in $(pwd)"
    echo "📁 Contents of current directory:"
    ls -la
    echo ""
    echo "🔍 Searching for pyproject.toml..."
    find . -name "pyproject.toml" -type f 2>/dev/null || echo "No pyproject.toml found anywhere"
    echo ""
    echo "⚠️  Falling back to requirements.txt installation..."
    
    if [ -f "requirements.txt" ]; then
        echo "📦 Installing from requirements.txt..."
        uv pip install --system -r requirements.txt
        echo "✅ Dependencies installed from requirements.txt"
    else
        echo "❌ Neither pyproject.toml nor requirements.txt found!"
        echo "📁 Available files:"
        ls -la
        exit 1
    fi
else
    echo "✅ Found pyproject.toml, installing with uv sync..."
    # Try UV sync first, fall back to pip if it fails
    if uv sync --no-dev --frozen; then
        echo "✅ Dependencies installed with uv sync"
    else
        echo "⚠️  uv sync failed, falling back to requirements.txt..."
        if [ -f "requirements.txt" ]; then
            uv pip install --system -r requirements.txt
            echo "✅ Dependencies installed from requirements.txt"
        else
            echo "❌ No fallback available!"
            exit 1
        fi
    fi
fi

echo "✅ Dependencies installed"
echo "   Core packages:"
echo "   - FastAPI (Web framework)"
echo "   - SQLAlchemy (Database ORM)"
echo "   - Pydantic (Data validation)"
echo "   - Alembic (Database migrations)"
echo "   - Redis (Caching & rate limiting)"
echo "   - Casbin (Authorization)"
echo ""

# Install and start Redis (if not available via Azure Redis Cache)
echo "🔴 Setting up Redis..."
if ! command -v redis-server &> /dev/null; then
    apt-get update -qq > /dev/null 2>&1
    apt-get install -y redis-server > /dev/null 2>&1
    echo "✅ Redis installed"
    
    # Start Redis in background
    redis-server --daemonize yes --bind 127.0.0.1 --port 6379 --maxmemory 100mb --maxmemory-policy allkeys-lru
    sleep 2
    
    # Check if Redis is running
    if redis-cli ping > /dev/null 2>&1; then
        echo "✅ Redis is running on localhost:6379"
    else
        echo "⚠️  Redis failed to start"
    fi
else
    echo "✅ Redis already available"
fi
echo ""

# Database setup check
echo "🗄️  Database Setup:"
echo "   Provider: PostgreSQL/Supabase"
echo "   Connection: Via environment variables"
echo "   Migrations: Will run automatically on startup"
echo ""

# Environment Configuration
echo "🔧 Environment Configuration:"
echo "   Environment: ${ENVIRONMENT:-production}"
echo "   Debug Mode: ${DEBUG:-False}"
echo "   Cache Enabled: ${CACHE_ENABLED:-True}"
echo "   Rate Limiting: ${LIMITER_ENABLED:-True}"
echo ""

# Run database migrations
echo "🔄 Running Database Migrations..."
if [ -f "alembic.ini" ]; then
    uv run alembic upgrade head
    echo "✅ Database migrations completed"
else
    echo "⚠️  No alembic.ini found, skipping migrations"
fi
echo ""

# Application Configuration
echo "🚀 Starting Application:"
echo "   App: WindX Product Configurator API"
echo "   Entry Point: main:app"
echo "   Workers: 4"
echo "   Timeout: 300s"
echo "   Bind: 0.0.0.0:8000"
echo "   Features:"
echo "   - Product Configuration Engine"
echo "   - Real-time Pricing Calculations"
echo "   - Template Management"
echo "   - Quote Generation with Snapshots"
echo "   - Order Management"
echo "   - Role-based Access Control (RBAC)"
echo "   - Hierarchical Attribute System (LTREE)"
echo ""
echo "=========================================="
echo ""

# Start the FastAPI application with Gunicorn
exec uv run gunicorn main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 300 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --preload
