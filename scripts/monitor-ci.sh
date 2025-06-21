#!/bin/bash

# Monitor CI/CD Pipeline Status
# Usage: ./scripts/monitor-ci.sh [branch_name] [interval_seconds]

BRANCH=${1:-$(git branch --show-current)}
INTERVAL=${2:-30}
PR_NUMBER=$(gh pr list --head "$BRANCH" --json number --jq '.[0].number')

echo "🔍 Monitoring CI/CD Pipeline for branch: $BRANCH"
echo "📋 PR Number: $PR_NUMBER"
echo "⏰ Check interval: ${INTERVAL}s"
echo "============================================"

monitor_pipeline() {
    while true; do
        echo "⏰ $(date '+%H:%M:%S') - Checking pipeline status..."
        
        # Check workflow runs for the branch
        if [ -n "$PR_NUMBER" ]; then
            echo "📊 PR Status:"
            gh pr status --json statusCheckRollup,reviewDecision,mergeable | jq -r '
                "Status Checks: " + (.statusCheckRollup // "none") + 
                "\nReview Decision: " + (.reviewDecision // "pending") + 
                "\nMergeable: " + (.mergeable // "unknown")'
            
            # Check for any failures
            FAILED_COUNT=$(gh run list --branch "$BRANCH" --limit 5 --json conclusion | jq '[.[] | select(.conclusion == "failure")] | length')
            
            if [ "$FAILED_COUNT" -gt 0 ]; then
                echo "❌ Found $FAILED_COUNT failed workflow runs!"
                echo "🔧 Would you like to create a fixup commit? (This will be handled interactively)"
                # Don't auto-execute fixup - let user decide
                break
            else
                echo "✅ No recent failures detected"
            fi
        else
            echo "ℹ️ No open PR found for branch $BRANCH"
        fi
        
        echo "================== Next check in ${INTERVAL}s =================="
        sleep "$INTERVAL"
    done
}

# Handle fixup workflow
handle_failure() {
    echo "🔧 Failure Detection - Fixup Workflow"
    echo "1. Identify the issue in the failed workflow"
    echo "2. Make necessary fixes"
    echo "3. Stage changes: git add ."
    echo "4. Create fixup commit: git commit --fixup=HEAD"
    echo "5. Interactive rebase: git rebase -i --autosquash HEAD~2"
    echo "6. Force push: git push --force-with-lease origin $BRANCH"
}

# Start monitoring
monitor_pipeline
