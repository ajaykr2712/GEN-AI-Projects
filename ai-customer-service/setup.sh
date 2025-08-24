#!/bin/bash

# AI Customer Service Assistant - Quick Start Script

echo "🤖 AI Customer Service Assistant - Quick Start"
echo "=============================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check dependencies
echo "📋 Checking dependencies..."

if ! command_exists python3; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

if ! command_exists node; then
    echo "❌ Node.js is required but not installed."
    exit 1
fi

echo "✅ Dependencies check passed"

# Setup backend
echo ""
echo "🔧 Setting up backend..."
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Copy environment file
if [ ! -f ".env" ]; then
    echo "Creating environment configuration..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your OpenAI API key before running the backend"
fi

# Initialize database
echo "Initializing database..."
python scripts/init_db.py

echo "✅ Backend setup completed"

# Setup frontend
echo ""
echo "🎨 Setting up frontend..."
cd ../frontend

# Install dependencies
echo "Installing Node.js dependencies..."
npm install

echo "✅ Frontend setup completed"

echo ""
echo "🚀 Setup completed successfully!"
echo ""
echo "To start the application:"
echo "1. Update backend/.env with your OpenAI API key"
echo "2. Start backend: cd backend && source venv/bin/activate && uvicorn main:app --reload"
echo "3. Start frontend: cd frontend && npm start"
echo ""
echo "Or use Docker: docker-compose up -d"
echo ""
echo "Default credentials:"
echo "- Admin: admin / admin123"
echo "- Demo: demo / demo123"
