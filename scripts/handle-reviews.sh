#!/bin/bash

# Handle PR Review Comments and Feedback
# Usage: ./scripts/handle-reviews.sh [pr_number]

BRANCH=$(git branch --show-current)
PR_NUMBER=${1:-$(gh pr list --head "$BRANCH" --json number --jq '.[0].number')}

if [ -z "$PR_NUMBER" ]; then
    echo "❌ No PR found for branch $BRANCH"
    exit 1
fi

echo "📋 PR Review Handler"
echo "===================="
echo "Branch: $BRANCH"
echo "PR Number: #$PR_NUMBER"
echo ""

# Check for new reviews
check_reviews() {
    echo "🔍 Checking for reviews..."
    
    REVIEWS=$(gh pr view "$PR_NUMBER" --json reviews --jq '.reviews | length')
    COMMENTS=$(gh pr view "$PR_NUMBER" --json comments --jq '.comments | length')
    
    echo "📊 Review Status:"
    echo "  - Reviews: $REVIEWS"
    echo "  - Comments: $COMMENTS"
    
    if [ "$REVIEWS" -gt 0 ] || [ "$COMMENTS" -gt 0 ]; then
        echo ""
        echo "📝 Recent Reviews:"
        gh pr view "$PR_NUMBER" --json reviews --jq '.reviews[] | "👤 " + .author.login + " (" + .state + "): " + (.body // "No comment")'
        
        echo ""
        echo "💬 Recent Comments:"
        gh pr view "$PR_NUMBER" --json comments --jq '.comments[] | "👤 " + .author.login + ": " + .body'
        
        echo ""
        echo "🔧 Action needed:"
        echo "1. Address feedback concerns"
        echo "2. Make necessary changes"
        echo "3. Push updates to continue the review cycle"
        
        return 1
    else
        echo "✅ No reviews or comments yet"
        return 0
    fi
}

# Monitor for changes
monitor_reviews() {
    while true; do
        echo "⏰ $(date '+%H:%M:%S') - Checking for new reviews..."
        
        if ! check_reviews; then
            echo ""
            read -p "🤔 Address feedback now? (y/N): " -n 1 -r
            echo ""
            
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                echo "🔧 Opening relevant files for editing..."
                echo "ℹ️ Make your changes, then run this script again to push updates"
                break
            fi
        fi
        
        echo "================== Next check in 60s =================="
        sleep 60
    done
}

# Push updates after addressing feedback
push_updates() {
    echo "🚀 Pushing Review Updates"
    echo "========================"
    
    if ! git diff --quiet || ! git diff --cached --quiet; then
        echo "📝 Changes detected. Staging and committing..."
        git add .
        
        read -p "💬 Commit message (or press Enter for default): " COMMIT_MSG
        
        if [ -z "$COMMIT_MSG" ]; then
            COMMIT_MSG="address review feedback"
        fi
        
        git commit -m "$COMMIT_MSG"
        git push origin "$BRANCH"
        
        echo "✅ Updates pushed successfully!"
        echo "🔔 Reviewers will be notified of changes"
    else
        echo "ℹ️ No changes to commit"
    fi
}

# Main menu
echo "Select an action:"
echo "1) Check current review status"
echo "2) Monitor for new reviews (continuous)"
echo "3) Push updates after addressing feedback"
echo "4) View PR details"
echo ""

read -p "Choose (1-4): " -n 1 -r CHOICE
echo ""

case $CHOICE in
    1)
        check_reviews
        ;;
    2)
        monitor_reviews
        ;;
    3)
        push_updates
        ;;
    4)
        gh pr view "$PR_NUMBER"
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac
