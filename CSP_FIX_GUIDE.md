# CSP (Content Security Policy) Fix Guide

## Problem
The app is running but the UI appears broken because the Content Security Policy is blocking external resources:
- Tailwind CSS from `cdn.tailwindcss.com`
- Lucide icons from `unpkg.com`
- Socket.IO from `cdn.socket.io`
- Inline styles and scripts

## Solutions

### Solution 1: Quick Fix (Environment Variable)
Add this environment variable to your Render deployment:

```
DISABLE_CSP=true
```

This will completely disable CSP while keeping other security headers active.

### Solution 2: Update CSP Policy (Recommended)
The CSP policy has been updated in `middleware/security_headers.py` to include all necessary external resources:

```python
'production': {
    'default-src': ["'self'"],
    'script-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'", 
                   "https://cdn.tailwindcss.com", "https://unpkg.com", 
                   "https://cdn.socket.io", "https://cdnjs.cloudflare.com"],
    'style-src': ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com", 
                  "https://cdn.tailwindcss.com", "https://unpkg.com"],
    'font-src': ["'self'", "https://fonts.gstatic.com", "data:"],
    'img-src': ["'self'", "data:", "https:", "blob:"],
    'connect-src': ["'self'", "https://api.openrouter.ai", "wss:", "ws:", "https:"],
    'frame-ancestors': ["'none'"],
    'base-uri': ["'self'"],
    'form-action': ["'self'"],
    'worker-src': ["'self'", "blob:"],
    'child-src': ["'self'", "blob:"]
}
```

## Deployment Steps

### For Render:

1. **Commit and Push Changes**
   ```bash
   cd /Users/copp1723/Desktop/swarm/mcp_new_project
   git add middleware/security_headers.py
   git commit -m "Fix CSP policy to allow required external resources"
   git push origin main
   ```

2. **Trigger Redeploy**
   - Render should automatically redeploy when you push
   - Or manually trigger in Render dashboard

3. **Alternative: Use Environment Variable**
   - Go to Render Dashboard
   - Navigate to your service
   - Go to Environment section
   - Add: `DISABLE_CSP=true`
   - Save and let it redeploy

### Verification

After deployment, check:
1. No CSP errors in browser console
2. Tailwind CSS styles are applied (modern UI)
3. Lucide icons are visible
4. Socket.IO connects successfully

## Additional Issues to Fix

### 1. Redis Connection
The logs show Redis connection errors. In Render:
- Use the internal Redis hostname (not localhost)
- Update `REDIS_URL` environment variable

### 2. Database Schema
There's a missing `timestamp` column error. This needs a database migration.

### 3. Static Files
Ensure all JavaScript files are being served correctly from the `/static` directory.

## Testing Locally

To test the CSP fix locally:

```bash
# Without CSP
DISABLE_CSP=true python app.py

# With updated CSP
python app.py
```

## Browser Testing

1. Open Developer Tools (F12)
2. Go to Network tab
3. Reload page
4. Check that all resources load (200 status)
5. Check Console tab for any CSP violations

## Rollback Plan

If issues persist:
1. Set `DISABLE_CSP=true` in Render
2. This provides immediate relief while debugging
3. Then work on fine-tuning the CSP policy

## Long-term Solution

Consider bundling external resources locally:
1. Download Tailwind CSS, Lucide, Socket.IO
2. Serve from `/static` directory
3. Update HTML to use local paths
4. Remove external URLs from CSP

This makes your app more reliable and faster to load.
