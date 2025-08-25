#!/bin/bash

# Workflow validation script
echo "🔍 Validating CI/CD workflow configuration..."

# Check if required files exist
echo "📁 Checking required files..."

files_to_check=(
    "backend/requirements.txt"
    "backend/main.py"
    "frontend/package.json"
    ".github/workflows/ci-cd.yml"
    ".markdownlint.json"
)

missing_files=()

for file in "${files_to_check[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file exists"
    else
        echo "❌ $file is missing"
        missing_files+=("$file")
    fi
done

# Check directory structure
echo ""
echo "📂 Checking directory structure..."

dirs_to_check=(
    "backend"
    "frontend"
    "backend/app"
    "backend/tests"
    ".github"
    ".github/workflows"
)

for dir in "${dirs_to_check[@]}"; do
    if [ -d "$dir" ]; then
        echo "✅ $dir directory exists"
    else
        echo "❌ $dir directory is missing"
        mkdir -p "$dir"
        echo "   Created $dir"
    fi
done

# Validate YAML syntax
echo ""
echo "🔧 Validating workflow YAML syntax..."

if command -v python3 &> /dev/null; then
    python3 -c "
import yaml
import sys

try:
    with open('.github/workflows/ci-cd.yml', 'r') as f:
        yaml.safe_load(f)
    print('✅ YAML syntax is valid')
except yaml.YAMLError as e:
    print(f'❌ YAML syntax error: {e}')
    sys.exit(1)
except FileNotFoundError:
    print('❌ Workflow file not found')
    sys.exit(1)
"
else
    echo "⚠️ Python not found, skipping YAML validation"
fi

# Summary
echo ""
echo "📊 Validation Summary:"
if [ ${#missing_files[@]} -eq 0 ]; then
    echo "🎉 All required files are present!"
    echo "✅ Your workflow should run without path errors"
else
    echo "⚠️ Missing files that may cause workflow errors:"
    for file in "${missing_files[@]}"; do
        echo "   - $file"
    done
fi

echo ""
echo "🚀 To fix remaining issues:"
echo "1. Add any missing files listed above"
echo "2. Set up GitHub secrets: OPENAI_API_KEY (optional)"
echo "3. Commit and push to trigger the workflow"
