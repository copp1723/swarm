#!/bin/bash

# CSP Fix Deployment Script

echo "🚀 Deploying CSP fixes to production..."

cd /Users/copp1723/Desktop/swarm/mcp_new_project

# Check git status
echo "📋 Current git status:"
git status --short

# Add changes
echo "➕ Adding CSP fixes..."
git add middleware/security_headers.py CSP_FIX_GUIDE.md

# Commit
echo "💾 Committing changes..."
git commit -m "Fix CSP policy to allow required external resources and add DISABLE_CSP env var option" || echo "Nothing to commit"

# Get current branch
BRANCH=$(git branch --show-current)
echo "🌿 Current branch: $BRANCH"

# Push to remote
echo "📤 Pushing to remote..."
git push origin $BRANCH

echo "✅ Deployment complete!"
echo ""
echo "Next steps:"
echo "1. Check Render dashboard for automatic redeploy"
echo "2. Or add DISABLE_CSP=true to Render environment variables for quick fix"
echo "3. Monitor the deployment logs"
