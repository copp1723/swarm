#!/bin/bash

# Merge PR Following Repository Conventions
# Usage: ./scripts/merge-pr.sh [pr_number] [merge_method]

BRANCH=$(git branch --show-current)
PR_NUMBER=${1:-$(gh pr list --head "$BRANCH" --json number --jq '.[0].number')}
MERGE_METHOD=${2:-""}

if [ -z "$PR_NUMBER" ]; then
    echo "❌ No PR found for branch $BRANCH"
    exit 1
fi

echo "🔀 PR Merge Handler"
echo "=================="
echo "Branch: $BRANCH"
echo "PR Number: #$PR_NUMBER"
echo ""

# Check PR status
check_pr_status() {
    echo "🔍 Checking PR status..."
    
    PR_STATUS=$(gh pr view "$PR_NUMBER" --json state,mergeable,reviewDecision --jq '{state, mergeable, reviewDecision}')
    
    STATE=$(echo "$PR_STATUS" | jq -r '.state')
    MERGEABLE=$(echo "$PR_STATUS" | jq -r '.mergeable')
    REVIEW_DECISION=$(echo "$PR_STATUS" | jq -r '.reviewDecision')
    
    echo "📊 PR Status:"
    echo "  - State: $STATE"
    echo "  - Mergeable: $MERGEABLE"
    echo "  - Review Decision: $REVIEW_DECISION"
    
    # Check CI status
    echo ""
    echo "🔍 Checking CI status..."
    
    CI_STATUS=$(gh pr checks "$PR_NUMBER" --json state,conclusion --jq 'map(select(.conclusion != null)) | map(.conclusion) | unique')
    
    if [ "$CI_STATUS" = '["success"]' ] || [ "$CI_STATUS" = '[]' ]; then
        echo "✅ All CI checks passing"
        CI_PASSING=true
    else
        echo "❌ CI checks failing or pending: $CI_STATUS"
        CI_PASSING=false
    fi
    
    # Determine if ready to merge
    if [ "$STATE" = "open" ] && [ "$MERGEABLE" = "MERGEABLE" ] && [ "$REVIEW_DECISION" = "APPROVED" ] && [ "$CI_PASSING" = true ]; then
        echo ""
        echo "✅ PR is ready to merge!"
        return 0
    else
        echo ""
        echo "❌ PR is not ready to merge:"
        [ "$STATE" != "open" ] && echo "  - PR is not open"
        [ "$MERGEABLE" != "MERGEABLE" ] && echo "  - PR has merge conflicts"
        [ "$REVIEW_DECISION" != "APPROVED" ] && echo "  - PR needs approval (current: $REVIEW_DECISION)"
        [ "$CI_PASSING" != true ] && echo "  - CI checks are not passing"
        return 1
    fi
}

# Detect repository merge strategy
detect_merge_strategy() {
    echo "🔍 Detecting repository merge strategy..."
    
    # Check repository settings via GitHub API
    REPO_INFO=$(gh api repos/copp1723/swarm --jq '{allow_squash_merge, allow_merge_commit, allow_rebase_merge, default_merge_method: (.squash_merge_commit_title // "merge")}')
    
    ALLOW_SQUASH=$(echo "$REPO_INFO" | jq -r '.allow_squash_merge')
    ALLOW_MERGE=$(echo "$REPO_INFO" | jq -r '.allow_merge_commit')
    ALLOW_REBASE=$(echo "$REPO_INFO" | jq -r '.allow_rebase_merge')
    
    echo "📋 Repository settings:"
    echo "  - Squash merge: $ALLOW_SQUASH"
    echo "  - Merge commit: $ALLOW_MERGE"
    echo "  - Rebase merge: $ALLOW_REBASE"
    
    # Determine default strategy
    if [ "$ALLOW_SQUASH" = "true" ]; then
        DEFAULT_METHOD="squash"
    elif [ "$ALLOW_REBASE" = "true" ]; then
        DEFAULT_METHOD="rebase"
    else
        DEFAULT_METHOD="merge"
    fi
    
    echo "🎯 Detected default method: $DEFAULT_METHOD"
    echo "$DEFAULT_METHOD"
}

# Execute merge
execute_merge() {
    local method=$1
    
    echo "🚀 Executing $method merge..."
    
    case $method in
        "squash")
            gh pr merge "$PR_NUMBER" --squash --auto
            ;;
        "rebase")
            gh pr merge "$PR_NUMBER" --rebase --auto
            ;;
        "merge")
            gh pr merge "$PR_NUMBER" --merge --auto
            ;;
        *)
            echo "❌ Unknown merge method: $method"
            return 1
            ;;
    esac
    
    if [ $? -eq 0 ]; then
        echo "✅ PR merged successfully!"
        
        # Clean up local branch
        echo "🧹 Cleaning up local branch..."
        git checkout main
        git pull origin main
        git branch -d "$BRANCH" 2>/dev/null || echo "ℹ️ Branch cleanup skipped (may have uncommitted changes)"
        
        echo "🎉 Merge process completed!"
    else
        echo "❌ Merge failed. Please check the error above."
        return 1
    fi
}

# Main workflow
main() {
    # Check if PR is ready
    if ! check_pr_status; then
        echo ""
        read -p "🤔 Continue anyway? (y/N): " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "❌ Merge cancelled."
            exit 1
        fi
    fi
    
    # Determine merge method
    if [ -z "$MERGE_METHOD" ]; then
        DETECTED_METHOD=$(detect_merge_strategy)
        echo ""
        echo "Merge options:"
        echo "1) squash - Squash all commits into one"
        echo "2) rebase - Rebase commits onto main"
        echo "3) merge - Create a merge commit"
        echo ""
        
        read -p "Choose merge method (1-3) or Enter for detected ($DETECTED_METHOD): " -n 1 -r
        echo ""
        
        case $REPLY in
            1)
                MERGE_METHOD="squash"
                ;;
            2)
                MERGE_METHOD="rebase"
                ;;
            3)
                MERGE_METHOD="merge"
                ;;
            "")
                MERGE_METHOD="$DETECTED_METHOD"
                ;;
            *)
                echo "❌ Invalid choice"
                exit 1
                ;;
        esac
    fi
    
    echo ""
    echo "🎯 Using merge method: $MERGE_METHOD"
    echo ""
    
    read -p "🚀 Proceed with merge? (y/N): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        execute_merge "$MERGE_METHOD"
    else
        echo "❌ Merge cancelled."
    fi
}

# Run main workflow
main
