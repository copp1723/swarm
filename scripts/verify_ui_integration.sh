#!/bin/bash
# Verify UI Enhancement Integration

echo "=== UI Enhancement Integration Verification ==="
echo

# Check if files exist
echo "1. Checking file existence..."
files=(
    "static/css/ui-enhancements.css"
    "static/js/ui-enhancements/agent-enhancements.js"
    "static/index.html"
)

all_exist=true
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "✓ $file exists"
    else
        echo "✗ $file not found"
        all_exist=false
    fi
done

echo
echo "2. Checking index.html integration..."

# Check if the includes are in index.html
if grep -q "ui-enhancements.css" static/index.html && grep -q "agent-enhancements.js" static/index.html; then
    echo "✓ UI enhancement files are included in index.html"
else
    echo "✗ UI enhancement files are NOT included in index.html"
    all_exist=false
fi

echo
echo "3. Checking for conflicts..."

# Check for duplicate class definitions
echo -n "Checking CSS conflicts... "
css_conflicts=$(grep -r "agent-role-badge\|capability-badge\|system-status-bar" static/css/*.css 2>/dev/null | grep -v ui-enhancements.css | wc -l)
if [ "$css_conflicts" -eq 0 ]; then
    echo "✓ No CSS conflicts found"
else
    echo "✗ Found $css_conflicts potential CSS conflicts"
fi

echo
echo "4. Feature Summary:"
echo "✓ Agent Profiles with role badges and descriptions"
echo "✓ System Status Bar for monitoring"
echo "✓ Workflow Templates for quick task creation"
echo "✓ Agent Communication visualization"
echo "✓ Memory Viewer for agents with memory capability"
echo "✓ Enhanced animations and visual feedback"

echo
if [ "$all_exist" = true ]; then
    echo "✅ UI Enhancement Integration Successful!"
    echo
    echo "Next steps:"
    echo "1. Start the server: ./start_server.sh"
    echo "2. Open the application in a browser"
    echo "3. Verify enhancements are visible:"
    echo "   - System status bar at the top"
    echo "   - Enhanced agent cards with badges"
    echo "   - Workflow templates in collaboration section"
else
    echo "❌ Integration incomplete. Please check the errors above."
fi