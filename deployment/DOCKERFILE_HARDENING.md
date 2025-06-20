# Dockerfile Hardening Implementation

This document explains the hardening improvements implemented in the Dockerfile according to the security requirements.

## Changes Made

### 1. Node.js Installation Moved to Builder Stage
- **Before**: Node.js was installed in the runtime stage, increasing final image size
- **After**: Node.js installation moved to builder stage with conditional copying to runtime
- **Benefit**: Smaller production images when Node.js isn't needed

### 2. Consolidated System Dependencies
The following system libraries are now installed once in the builder stage:
- `libpq-dev` - PostgreSQL development headers
- `gcc` - GNU C compiler
- `g++` - GNU C++ compiler  
- `libc6-dev` - GNU C library development files
- `libffi-dev` - Foreign Function Interface library development files
- `libssl-dev` - Secure Sockets Layer toolkit development files

**Benefit**: Fixes `psycopg2` and `gevent` compilation errors, especially when switching to Alpine base images.

### 3. Development Dependencies Control
Added `ARG INSTALL_DEV=false` build argument:
- **Production builds**: Skip Node.js/NPM installation when `INSTALL_DEV=false`
- **Development builds**: Include Node.js/NPM when `INSTALL_DEV=true`
- **Integration**: Works with `DISABLE_MCP_FILESYSTEM=true` for minimal production images

### 4. Port Exposure with Fallback
- **Implementation**: `EXPOSE ${PORT:-10000}`
- **Benefit**: Always exposes a port even if `$PORT` environment variable is not set
- **Fallback**: Uses port 10000 as default

## Usage

### Production Build (No Node.js)
```bash
docker build -f deployment/Dockerfile .
# or explicitly
docker build -f deployment/Dockerfile --build-arg INSTALL_DEV=false .
```

### Development Build (With Node.js)
```bash
docker build -f deployment/Dockerfile --build-arg INSTALL_DEV=true .
```

### Docker Compose
The docker-compose.yml supports the build argument via environment variable:

```bash
# Production
INSTALL_DEV=false docker-compose up --build

# Development  
INSTALL_DEV=true docker-compose up --build
```

## Security Improvements

1. **Smaller Attack Surface**: Production images exclude unnecessary Node.js binaries
2. **Dependency Consolidation**: All build dependencies installed once, reducing complexity
3. **Reliable Port Exposure**: Guaranteed port exposure prevents deployment issues
4. **Multi-stage Optimization**: Build artifacts separated from runtime environment

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `INSTALL_DEV` | `false` | Controls Node.js installation |
| `PORT` | `10000` | Application listen port |
| `DISABLE_MCP_FILESYSTEM` | - | When `true`, use minimal image without Node.js |

## Compatibility

- ✅ Works with existing application code
- ✅ Maintains compatibility with Render deployment
- ✅ Supports both development and production workflows
- ✅ Alpine and Debian base image compatible

