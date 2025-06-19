# Group Chat Testing Guide - Updated

## Changes Made

1. **Group chat now takes focus** - The main chat interface is hidden when group chat starts
2. **Centered positioning** - Group chat appears centered on screen, not in bottom-right
3. **Larger window** - 90% width (max 1200px) and 85% height for better visibility
4. **Higher z-index** - Set to 9999 to ensure it's always on top
5. **Auto-start collaboration** - The initial message automatically starts the agent collaboration
6. **Better error handling** - More robust polling with timeout after 2 minutes

## How to Debug

If the group chat window doesn't appear:

1. **Check browser console** for errors
2. **Run manual test** in console:
   ```javascript
   // Load test script
   const script = document.createElement('script');
   script.type = 'module';
   script.src = 'js/test-group-chat.js';
   document.head.appendChild(script);
   
   // After it loads, run:
   window.testGroupChat();
   ```

3. **Check if window is off-screen**:
   ```javascript
   // Find all group chat windows
   document.querySelectorAll('.group-chat-window').forEach(el => {
       console.log('Group chat found:', el);
       console.log('Position:', el.style.top, el.style.left);
       console.log('Z-index:', el.style.zIndex);
   });
   ```

# Group Chat Testing Guide

## How to Test the Group Chat Feature

1. **Open the application** in your browser (usually at http://localhost:5000)

2. **Select any agent** from the sidebar (e.g., General Assistant)

3. **Test single agent mentions:**
   - Type: `@coding agent can you help with this?`
   - Or: `@codingagent can you help with this?`
   - A group chat window should pop up with you and the Coding Agent

4. **Test multiple agent mentions:**
   - Type: `@coding agent and @qa engineer let's collaborate on testing`
   - A group chat window should appear with all three agents

5. **Test different mention formats:**
   - `@product agent` (with space)
   - `@productagent` (without space)
   - `@devops engineer` (multi-word agent name)
   - `@devopsengineer` (multi-word without spaces)

## Expected Behavior

- When you mention one or more agents using @ symbol, a floating group chat window should appear
- The window shows all participating agents in the title
- Your original message appears in the group chat
- The window is draggable and can be minimized/closed
- Directory context from your current chat is preserved
- You get a notification in your original chat that a group chat was started

## Features of the Group Chat Window

- **Draggable**: Click and drag the header to move the window
- **Minimize/Maximize**: Click the minus button to minimize
- **Close**: Click the X button to close the chat
- **Real-time updates**: Messages appear as agents respond
- **Visual indicators**: Different colors for different agents
- **Directory context**: Shows the working directory if one is selected

## Troubleshooting

If the group chat doesn't appear:
1. Check the browser console for any errors
2. Make sure the agent names are spelled correctly
3. Try refreshing the page
4. Ensure JavaScript is enabled in your browser