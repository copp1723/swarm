#!/bin/bash

# Handle CI/CD Failure with Clean History Management
# Usage: ./scripts/handle-ci-failure.sh [target_commit_sha]

set -e

TARGET_COMMIT=${1:-HEAD}
BRANCH=$(git branch --show-current)

echo "🔧 CI/CD Failure Handler"
echo "========================"
echo "Branch: $BRANCH"
echo "Target commit: $TARGET_COMMIT"
echo ""

# Check if there are unstaged changes
if ! git diff --quiet; then
    echo "📝 Unstaged changes detected. Staging them..."
    git add .
fi

# Check if there are staged changes
if git diff --cached --quiet; then
    echo "❌ No staged changes found. Please make your fixes first."
    exit 1
fi

echo "📋 Staged changes:"
git diff --cached --name-only

echo ""
read -p "🤔 Create fixup commit for $TARGET_COMMIT? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Create fixup commit
    echo "🔨 Creating fixup commit..."
    git commit --fixup="$TARGET_COMMIT"
    
    # Count commits to rebase
    COMMIT_COUNT=$(git rev-list --count HEAD ^origin/main)
    
    echo "📚 Rebasing last $COMMIT_COUNT commits with autosquash..."
    
    # Interactive rebase with autosquash
    GIT_SEQUENCE_EDITOR=true git rebase -i --autosquash HEAD~$COMMIT_COUNT
    
    echo "✅ Rebase completed successfully!"
    echo ""
    echo "🚀 Ready to push. Commands to run:"
    echo "   git push --force-with-lease origin $BRANCH"
    echo ""
    
    read -p "🚀 Push changes now? (y/N): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git push --force-with-lease origin "$BRANCH"
        echo "✅ Changes pushed successfully!"
        
        # Wait a moment and check CI status
        echo "⏰ Waiting 30 seconds for CI to start..."
        sleep 30
        
        echo "🔍 Checking new CI status..."
        gh run list --branch "$BRANCH" --limit 3
    else
        echo "ℹ️ Skipped push. Run manually when ready:"
        echo "   git push --force-with-lease origin $BRANCH"
    fi
else
    echo "❌ Fixup commit cancelled."
fi
