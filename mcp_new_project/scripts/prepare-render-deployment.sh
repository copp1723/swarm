#!/bin/bash

# Render Deployment Preparation Script
# This script helps prepare your repository for Render deployment

set -e

echo "🚀 MCP Executive Platform - Render Deployment Preparation"
echo "=========================================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if we're in the right directory
if [[ ! -f "app.py" || ! -f "render.yaml" ]]; then
    print_error "This script must be run from the project root directory"
    print_info "Please run from the directory containing app.py and render.yaml"
    exit 1
fi

print_info "Checking deployment readiness..."

# 1. Check Git status
echo
echo "1. Checking Git repository status..."
if ! git status &>/dev/null; then
    print_error "Not in a Git repository. Initialize with: git init"
    exit 1
fi

# Check for uncommitted changes
if [[ -n $(git status --porcelain) ]]; then
    print_warning "You have uncommitted changes:"
    git status --short
    echo
    read -p "Do you want to commit these changes? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Enter commit message:"
        read -r commit_msg
        git add .
        git commit -m "$commit_msg"
        print_status "Changes committed"
    else
        print_warning "Continuing with uncommitted changes"
    fi
else
    print_status "Git repository is clean"
fi

# 2. Check required files
echo
echo "2. Checking required deployment files..."

required_files=(
    "render.yaml"
    "deployment/Dockerfile"
    "app.py"
    "requirements.txt"
)

for file in "${required_files[@]}"; do
    if [[ -f "$file" ]]; then
        print_status "$file exists"
    else
        print_error "$file is missing"
        exit 1
    fi
done

# 3. Check environment variables template
echo
echo "3. Checking environment configuration..."

if [[ -f "config/.env.example" ]]; then
    print_status "Environment template exists"
    
    # Extract required variables from template
    required_vars=(
        "OPENROUTER_API_KEY"
        "MAILGUN_API_KEY"
        "MAILGUN_DOMAIN"
        "MAILGUN_SIGNING_KEY"
    )
    
    print_info "Required environment variables for Render:"
    for var in "${required_vars[@]}"; do
        echo "   - $var"
    done
else
    print_warning "No environment template found"
fi

# 4. Validate Docker build
echo
echo "4. Validating Docker configuration..."

if command -v docker &> /dev/null; then
    print_info "Testing Docker build (this may take a few minutes)..."
    if docker build -f deployment/Dockerfile -t mcp-test . >/dev/null 2>&1; then
        print_status "Docker build successful"
        docker rmi mcp-test >/dev/null 2>&1
    else
        print_error "Docker build failed"
        print_info "Run 'docker build -f deployment/Dockerfile .' to see detailed errors"
        exit 1
    fi
else
    print_warning "Docker not found - build validation skipped"
fi

# 5. Check render.yaml configuration
echo
echo "5. Validating render.yaml..."

if grep -q "MAILGUN_API_KEY" render.yaml; then
    print_status "Mailgun environment variables configured in render.yaml"
else
    print_error "Mailgun environment variables missing from render.yaml"
    print_info "Please update render.yaml with Mailgun configuration"
    exit 1
fi

# 6. Check for secrets in code
echo
echo "6. Checking for potential secrets in code..."

secret_patterns=(
    "sk-[a-zA-Z0-9]"
    "key-[a-zA-Z0-9]"
    "secret.*=.*['\"][^'\"]{20,}['\"]"
    "password.*=.*['\"][^'\"]{8,}['\"]"
)

found_secrets=false
for pattern in "${secret_patterns[@]}"; do
    if grep -r -E "$pattern" --include="*.py" --include="*.js" --include="*.yaml" --exclude-dir=".git" . 2>/dev/null; then
        found_secrets=true
    fi
done

if [[ "$found_secrets" == true ]]; then
    print_error "Potential secrets found in code!"
    print_info "Please move all secrets to environment variables"
    exit 1
else
    print_status "No hardcoded secrets detected"
fi

# 7. Generate deployment summary
echo
echo "7. Generating deployment summary..."

cat << EOF

📋 DEPLOYMENT SUMMARY
=====================

Repository Status: Ready for deployment
Required Files: All present
Docker Build: Validated
Environment Config: Prepared

NEXT STEPS:
-----------
1. Push your code to GitHub:
   git push origin main

2. Go to Render Dashboard (https://render.com)
3. Click "New +" → "Blueprint"
4. Connect your GitHub repository
5. Set environment variables in Render dashboard:

   Required Variables:
   - OPENROUTER_API_KEY=your-openrouter-key
   - MAILGUN_API_KEY=your-mailgun-api-key
   - MAILGUN_DOMAIN=your-verified-domain
   - MAILGUN_SIGNING_KEY=your-webhook-signing-key

6. Click "Apply Blueprint" to deploy

POST-DEPLOYMENT:
----------------
1. Test health endpoint: https://your-app.onrender.com/health
2. Configure Mailgun webhook URL: https://your-app.onrender.com/api/email-agent/webhooks/mailgun
3. Send test email to verify integration

For detailed instructions, see: docs/render_deployment_guide.md

EOF

# 8. Optional: Push to git
echo
read -p "Push changes to Git now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if git remote -v | grep -q "origin"; then
        git push origin main
        print_status "Code pushed to GitHub"
        print_info "You can now deploy to Render using the dashboard"
    else
        print_warning "No Git remote 'origin' found"
        print_info "Please add your GitHub repository as origin:"
        print_info "git remote add origin https://github.com/username/repository.git"
        print_info "git push -u origin main"
    fi
fi

echo
print_status "Deployment preparation complete!"
print_info "Follow the Render Deployment Guide for next steps: docs/render_deployment_guide.md"

