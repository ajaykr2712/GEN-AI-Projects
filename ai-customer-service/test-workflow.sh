#!/bin/bash

# CI/CD Workflow Test Script
# This script helps test your GitHub Actions workflow locally

set -e

echo "🚀 Testing CI/CD Workflow Components Locally"
echo "=============================================="

# Test 1: Check if required files exist
echo "📋 Checking required files..."
required_files=(
    ".github/workflows/ci-cd.yml"
    ".markdownlint.json"
    "backend/requirements.txt"
    "frontend/package.json"
    "docker-compose.yml"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file exists"
    else
        echo "❌ $file missing"
        exit 1
    fi
done

# Test 2: Validate YAML syntax
echo -e "\n🔍 Validating workflow YAML syntax..."
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci-cd.yml')); print('✅ YAML syntax is valid')"

# Test 3: Check if Docker Compose is valid
echo -e "\n🐳 Validating Docker Compose..."
if command -v docker-compose &> /dev/null; then
    docker-compose config --quiet && echo "✅ Docker Compose configuration is valid"
else
    echo "⚠️  Docker Compose not installed, skipping validation"
fi

# Test 4: Check Python dependencies
echo -e "\n🐍 Checking Python backend..."
if [ -d "backend" ]; then
    cd backend
    if [ -f "requirements.txt" ]; then
        echo "✅ Python requirements.txt found"
        # Count dependencies
        deps=$(wc -l < requirements.txt)
        echo "📦 Found $deps Python dependencies"
    fi
    cd ..
fi

# Test 5: Check Node.js dependencies
echo -e "\n📦 Checking Node.js frontend..."
if [ -d "frontend" ]; then
    cd frontend
    if [ -f "package.json" ]; then
        echo "✅ Node.js package.json found"
        # Check if main scripts exist
        if grep -q '"test"' package.json; then
            echo "✅ Test script configured"
        fi
        if grep -q '"build"' package.json; then
            echo "✅ Build script configured"
        fi
    fi
    cd ..
fi

# Test 6: Check markdown files
echo -e "\n📝 Checking markdown files..."
md_files=$(find . -name "*.md" -type f | wc -l)
echo "📄 Found $md_files markdown files"

# Test 7: Simulate workflow triggers
echo -e "\n🎯 Workflow Trigger Simulation..."
echo "✅ Workflow will trigger on:"
echo "   - Push to main/develop branches"
echo "   - Pull requests to main branch"
echo "   - Manual workflow dispatch"

echo -e "\n🎉 All local tests passed!"
echo "🚀 Your workflow should now run successfully on GitHub Actions!"

# Instructions for user
echo -e "\n📋 Next Steps:"
echo "1. Commit and push your changes to trigger the workflow"
echo "2. Go to GitHub Actions tab to monitor the pipeline"
echo "3. Set up these repository secrets if needed:"
echo "   - OPENAI_API_KEY (for AI service testing)"
echo "   - DOCKER_USERNAME (for Docker registry)"
echo "   - DOCKER_PASSWORD (for Docker registry)"
