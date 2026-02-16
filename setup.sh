#!/bin/bash

# OPAL Platform Setup Script
# This script helps you set up the OPAL platform quickly

set -e

echo "⚡ OPAL Platform Setup"
echo "====================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env exists
if [ -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file already exists${NC}"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup cancelled."
        exit 0
    fi
fi

# Copy example env
echo "📋 Creating .env file from template..."
cp .env.example .env
echo -e "${GREEN}✓${NC} Created .env file"
echo ""

# Prompt for Supabase credentials
echo "🗄️  Supabase Configuration"
echo "Get these from: https://app.supabase.com/project/_/settings/api"
echo ""

read -p "Supabase URL: " SUPABASE_URL
read -p "Supabase Service Role Key: " SUPABASE_SERVICE_ROLE_KEY
read -p "Supabase Anon Key: " SUPABASE_ANON_KEY
read -p "Database URL: " DATABASE_URL

# Update .env file
sed -i.bak "s|SUPABASE_URL=.*|SUPABASE_URL=$SUPABASE_URL|g" .env
sed -i.bak "s|SUPABASE_SERVICE_ROLE_KEY=.*|SUPABASE_SERVICE_ROLE_KEY=$SUPABASE_SERVICE_ROLE_KEY|g" .env
sed -i.bak "s|SUPABASE_ANON_KEY=.*|SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY|g" .env
sed -i.bak "s|DATABASE_URL=.*|DATABASE_URL=$DATABASE_URL|g" .env

rm .env.bak

echo -e "${GREEN}✓${NC} Updated .env with Supabase credentials"
echo ""

# API Key configuration
echo "🔐 API Key Configuration"
read -p "API Key (default: dev_testkey123): " API_KEY
API_KEY=${API_KEY:-dev_testkey123}
sed -i.bak "s|API_KEYS=.*|API_KEYS=$API_KEY|g" .env
rm .env.bak
echo -e "${GREEN}✓${NC} Set API key"
echo ""

# Frontend configuration
echo "🎨 Frontend Configuration"
cd frontend
if [ -f .env ]; then
    echo -e "${YELLOW}⚠️  frontend/.env already exists${NC}"
else
    cat > .env << EOF
VITE_API_URL=http://localhost:8080
VITE_API_KEY=$API_KEY
EOF
    echo -e "${GREEN}✓${NC} Created frontend/.env"
fi
cd ..
echo ""

# Check for Docker
echo "🐳 Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗${NC} Docker not found"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    echo ""
    echo "Alternatively, you can run services manually (see README.md)"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}✗${NC} docker-compose not found"
    echo "Please install docker-compose: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✓${NC} Docker found"
echo ""

# Check Node.js
echo "📦 Checking Node.js..."
if ! command -v node &> /dev/null; then
    echo -e "${RED}✗${NC} Node.js not found"
    echo "Please install Node.js 18+: https://nodejs.org/"
    exit 1
fi

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo -e "${RED}✗${NC} Node.js version $NODE_VERSION is too old"
    echo "Please install Node.js 18 or higher"
    exit 1
fi

echo -e "${GREEN}✓${NC} Node.js $(node -v) found"
echo ""

# Install frontend dependencies
echo "📦 Installing frontend dependencies..."
cd frontend
npm install
echo -e "${GREEN}✓${NC} Frontend dependencies installed"
cd ..
echo ""

# Summary
echo "✅ Setup Complete!"
echo "=================="
echo ""
echo "Next steps:"
echo ""
echo "1. Start backend services:"
echo "   ${GREEN}docker-compose up -d${NC}"
echo ""
echo "2. View backend logs:"
echo "   ${GREEN}docker-compose logs -f${NC}"
echo ""
echo "3. Start frontend (in another terminal):"
echo "   ${GREEN}cd frontend && npm run dev${NC}"
echo ""
echo "4. Open your browser:"
echo "   ${GREEN}http://localhost:5173${NC}"
echo ""
echo "📚 Documentation:"
echo "   - README.md - Getting started"
echo "   - FRONTEND-GUIDE.md - Frontend usage"
echo "   - BACKEND-DEPLOYMENT.md - Deploy to production"
echo ""
echo "🐛 Troubleshooting:"
echo "   - Check logs: docker-compose logs -f"
echo "   - Test health: curl http://localhost:8080/healthz"
echo "   - See DEPLOYMENT-FIXES.md"
echo ""
echo "Happy processing! ⚡"
