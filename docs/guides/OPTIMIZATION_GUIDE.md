# Performance Optimization Guide

This guide documents the performance optimizations implemented for the SWARM MCP project.

## Phase 1: Server and Database Optimization

### Task 1: Production Server Configuration ✅

**Status:** Complete

**Changes:**
- Created `render.yaml` with Gunicorn + Uvicorn configuration
- Configured 4 worker processes for better concurrency
- Added proper environment variable management

**Benefits:**
- Replaces Flask development server with production-ready ASGI server
- Handles multiple concurrent requests efficiently
- Supports both sync and async request handling

### Task 2: Async Database Implementation ✅

**Status:** Complete

**Changes:**
1. **Added async database dependencies** in `requirements.txt`:
   - `sqlalchemy[asyncio]` - Async SQLAlchemy support
   - `asyncpg` - PostgreSQL async driver
   - `aiosqlite` - SQLite async driver (for development)
   - `gunicorn` and `uvicorn` - Production servers

2. **Created async database infrastructure**:
   - `utils/async_database.py` - Async database manager
   - `repositories/async_repositories.py` - Async repository classes
   - `utils/db_init.py` - Database initialization utilities

3. **Updated application**:
   - Added health check endpoint (`/health`) that uses async database
   - Initialize both sync and async databases on startup
   - Maintains backward compatibility with existing sync code

**Benefits:**
- Non-blocking database operations
- Better performance under load
- Gradual migration path from sync to async

## Migration Guide

### Step 1: Deploy with New Configuration

1. Commit all changes:
```bash
cd ~/Desktop/SWARM/mcp_new_project/
git add .
git commit -m "feat: add production server config and async database support"
git push
```

2. Update Render configuration to use `render.yaml`

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Test Health Endpoint

Once deployed, test the health endpoint:
```bash
curl https://your-app.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-17T10:30:00",
  "database": "connected",
  "async_database": "connected",
  "mcp_servers": "initialized",
  "response_time_ms": 15.2
}
```

### Step 4: Gradual Migration to Async

You can now gradually migrate endpoints to use async database operations:

**Example - Converting a sync endpoint to async:**

```python
# Old sync code
@app.route('/api/messages')
def get_messages():
    messages = db.session.query(Message).all()
    return jsonify([m.to_dict() for m in messages])

# New async code
@app.route('/api/messages')
async def get_messages():
    messages = await AsyncMessageRepository.get_recent_messages()
    return jsonify([m.to_dict() for m in messages])
```

## Next Steps

### Phase 2: Caching Implementation
- Add Redis for caching frequently accessed data
- Implement caching decorators
- Cache API responses and database queries

### Phase 3: Frontend Optimization
- Implement lazy loading for agent components
- Add virtual scrolling for long conversations
- Optimize bundle size with code splitting

### Phase 4: Background Task Processing
- Move heavy operations to background tasks
- Implement task queue with Celery
- Add progress tracking for long-running operations

## Performance Monitoring

Monitor these metrics after deployment:
- Response times (should decrease by 30-50%)
- Concurrent request handling (should increase 4x)
- Database query times (async queries should be faster under load)
- Memory usage (should remain stable with connection pooling)

## Troubleshooting

### Database Connection Issues
- Check `DATABASE_URL` environment variable
- Ensure it's in the correct format for async drivers
- Verify connection pooling settings

### Health Check Failures
- Check application logs for specific errors
- Verify database connectivity
- Ensure async event loop is running properly

### Performance Not Improving
- Verify Gunicorn is using Uvicorn workers
- Check worker count matches CPU cores
- Monitor for blocking operations in async code