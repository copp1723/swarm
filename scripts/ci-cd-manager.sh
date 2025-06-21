#!/bin/bash

# Master CI/CD Management Script
# Orchestrates pipeline monitoring, failure handling, review management, and merging
# Usage: ./scripts/ci-cd-manager.sh [action]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRANCH=$(git branch --show-current)
PR_NUMBER=$(gh pr list --head "$BRANCH" --json number --jq '.[0].number 2>/dev/null' || echo "")

echo "🚀 SWARM CI/CD Manager"
echo "======================"
echo "Branch: $BRANCH"
echo "PR: ${PR_NUMBER:-"No active PR"}"
echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Display current status
show_status() {
    echo "📊 Current Status"
    echo "=================="
    
    if [ -n "$PR_NUMBER" ]; then
        echo "🔍 PR #$PR_NUMBER Status:"
        gh pr view "$PR_NUMBER" --json state,reviewDecision,mergeable --jq '"State: " + .state + "\nReview: " + (.reviewDecision // "pending") + "\nMergeable: " + (.mergeable // "unknown")'
        
        echo ""
        echo "🔍 CI/CD Pipeline:"
        CI_STATUS=$(gh pr checks "$PR_NUMBER" --json state,conclusion 2>/dev/null || echo "[]")
        if [ "$CI_STATUS" != "[]" ]; then
            echo "$CI_STATUS" | jq -r '.[] | "  " + .name + ": " + (.conclusion // .state)'
        else
            echo "  No CI checks found"
        fi
        
        echo ""
        echo "📝 Recent Activity:"
        gh pr view "$PR_NUMBER" --json comments,reviews --jq '"Comments: " + (.comments | length | tostring) + "\nReviews: " + (.reviews | length | tostring)'
    else
        echo "ℹ️ No active PR for current branch"
        echo "💡 Consider creating a PR first"
    fi
}

# Main menu
show_menu() {
    echo ""
    echo "Available Actions:"
    echo "=================="
    echo "1) 📊 Show current status"
    echo "2) 👀 Monitor CI/CD pipeline (continuous)"
    echo "3) 🔧 Handle CI/CD failure (fixup workflow)"
    echo "4) 💬 Monitor & handle reviews"
    echo "5) 🚀 Merge PR (when ready)"
    echo "6) 🛠️  Complete workflow (monitor → handle → merge)"
    echo "7) ❌ Exit"
    echo ""
}

# Complete workflow automation
run_complete_workflow() {
    echo "🛠️ Starting Complete CI/CD Workflow"
    echo "===================================="
    
    if [ -z "$PR_NUMBER" ]; then
        echo "❌ No active PR found. Create a PR first."
        return 1
    fi
    
    echo "Step 1: Checking initial status..."
    show_status
    
    echo ""
    echo "Step 2: Monitoring pipeline..."
    echo "Press Ctrl+C to stop monitoring and continue to next step"
    
    # Monitor with timeout
    timeout 300 "$SCRIPT_DIR/monitor-ci.sh" "$BRANCH" 60 || echo "⏰ Monitoring timeout reached"
    
    echo ""
    echo "Step 3: Checking for reviews..."
    "$SCRIPT_DIR/handle-reviews.sh" "$PR_NUMBER"
    
    echo ""
    echo "Step 4: Final merge check..."
    "$SCRIPT_DIR/merge-pr.sh" "$PR_NUMBER"
}

# Handle user input
handle_action() {
    local action=$1
    
    case $action in
        1|"status")
            show_status
            ;;
        2|"monitor")
            echo "🔍 Starting CI/CD monitoring..."
            "$SCRIPT_DIR/monitor-ci.sh" "$BRANCH"
            ;;
        3|"fix"|"fixup")
            echo "🔧 Starting failure handler..."
            "$SCRIPT_DIR/handle-ci-failure.sh"
            ;;
        4|"review"|"reviews")
            if [ -z "$PR_NUMBER" ]; then
                echo "❌ No active PR found"
                return 1
            fi
            echo "💬 Starting review handler..."
            "$SCRIPT_DIR/handle-reviews.sh" "$PR_NUMBER"
            ;;
        5|"merge")
            if [ -z "$PR_NUMBER" ]; then
                echo "❌ No active PR found"
                return 1
            fi
            echo "🚀 Starting merge process..."
            "$SCRIPT_DIR/merge-pr.sh" "$PR_NUMBER"
            ;;
        6|"complete"|"workflow")
            run_complete_workflow
            ;;
        7|"exit"|"quit")
            echo "👋 Goodbye!"
            exit 0
            ;;
        *)
            echo "❌ Invalid action: $action"
            return 1
            ;;
    esac
}

# Command line argument handling
if [ $# -gt 0 ]; then
    # Direct action from command line
    ACTION=$1
    show_status
    echo ""
    handle_action "$ACTION"
else
    # Interactive mode
    while true; do
        show_status
        show_menu
        
        read -p "Choose action (1-7): " -r ACTION
        echo ""
        
        if ! handle_action "$ACTION"; then
            echo "Please try again."
        fi
        
        echo ""
        read -p "Press Enter to continue or 'q' to quit: " -r CONTINUE
        if [ "$CONTINUE" = "q" ]; then
            echo "👋 Goodbye!"
            break
        fi
        
        clear
    done
fi
