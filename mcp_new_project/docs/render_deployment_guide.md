# Render Deployment Guide for MCP Executive Platform

## Overview

This guide covers deploying the MCP Executive Platform to Render with public webhook endpoints for Mailgun integration.

## Prerequisites

1. **Render Account**: Sign up at [render.com](https://render.com)
2. **GitHub Repository**: Code must be in a GitHub repository
3. **Mailgun Account**: For email webhook integration
4. **Environment Variables**: Gather all required credentials

## Deployment Steps

### Step 1: Prepare Your Repository

1. **Ensure files are committed**:
   ```bash
   git add .
   git commit -m "Prepare for Render deployment"
   git push origin main
   ```

2. **Verify deployment files exist**:
   - `render.yaml` ✓ (updated with Mailgun env vars)
   - `deployment/Dockerfile` ✓
   - `requirements.txt` ✓

### Step 2: Connect Repository to Render

1. **Log into Render Dashboard**
2. **Click "New +"** → **"Blueprint"**
3. **Connect your GitHub repository**
4. **Select the repository** containing your MCP Executive Platform
5. **Choose the branch** (usually `main`)

### Step 3: Configure Environment Variables

In the Render dashboard, you'll need to set these environment variables:

#### Required Variables
```bash
# OpenRouter (AI Model API)
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# Mailgun (Email Service)
MAILGUN_API_KEY=your-mailgun-api-key
MAILGUN_DOMAIN=your-domain.com  
MAILGUN_SIGNING_KEY=your-webhook-signing-key

# Optional - Additional Services
SUPERMEMORY_API_KEY=your-supermemory-key  # If using Supermemory
GITHUB_PAT=ghp_your-github-token          # If using GitHub integration
```

#### Get Mailgun Credentials

1. **Login to Mailgun Dashboard**
2. **API Key**: Go to **Settings** → **API Keys** → Copy **Private API Key**
3. **Domain**: Your verified domain (e.g., `mg.yourdomain.com`)
4. **Signing Key**: Go to **Settings** → **Webhooks** → **HTTP webhook signing key**

### Step 4: Deploy Services

1. **Click "Apply Blueprint"** in Render
2. **Wait for deployment** (5-10 minutes)
3. **Monitor deployment logs** for any errors

The blueprint will create:
- **Web Service**: `swarm-mcp-app` (your main application)
- **Worker Service**: `swarm-celery-worker` (background tasks)
- **Redis Service**: `swarm-redis` (cache and message broker)
- **PostgreSQL Database**: `swarm-db` (persistent storage)

### Step 5: Verify Deployment

1. **Check service status** in Render dashboard
2. **Test health endpoint**:
   ```bash
   curl https://your-app-name.onrender.com/health
   ```
3. **Expected response**:
   ```json
   {
     "status": "healthy",
     "database": "connected",
     "async_database": "connected",
     "mcp_servers": "initialized"
   }
   ```

### Step 6: Configure Mailgun Webhooks

Once deployed, configure Mailgun to send webhooks to your Render URL:

#### Get Your Webhook URL
Your webhook URL will be:
```
https://your-app-name.onrender.com/api/email-agent/webhooks/mailgun
```

#### Configure in Mailgun Dashboard

1. **Go to Mailgun Dashboard** → **Webhooks**
2. **Add new webhook** with:
   - **URL**: `https://your-app-name.onrender.com/api/email-agent/webhooks/mailgun`
   - **Events**: Select events you want to track (e.g., `delivered`, `opened`, `clicked`)

#### Or Use Mailgun API

```bash
curl -s --user 'api:YOUR_MAILGUN_API_KEY' \
  https://api.mailgun.net/v3/domains/YOUR_DOMAIN/webhooks \
  -F id='delivered' \
  -F url='https://your-app-name.onrender.com/api/email-agent/webhooks/mailgun'
```

### Step 7: Test the Integration

#### Test Health Endpoint
```bash
curl https://your-app-name.onrender.com/api/email-agent/health
```

#### Test Webhook (using test script)
```bash
# Update the URL in test-mailgun-webhook.py
WEBHOOK_URL = "https://your-app-name.onrender.com/api/email-agent/webhooks/mailgun"

# Run the test
python test-mailgun-webhook.py
```

#### Send Real Test Email
Send an email to your configured Mailgun address and verify:
1. Webhook is received (check Render logs)
2. Task is created in the system
3. Background processing works

## Monitoring and Maintenance

### View Logs
```bash
# Install Render CLI
npm install -g @render-com/cli

# View live logs
render logs -s your-service-id --tail
```

### Monitor Resources
- **CPU/Memory usage** in Render dashboard
- **Database connections** in PostgreSQL metrics
- **Redis memory usage** in Redis service metrics

### Update Deployment
```bash
# Push changes to trigger deployment
git add .
git commit -m "Update feature"
git push origin main

# Render will auto-deploy if autoDeploy is enabled
```

## Custom Domain (Optional)

### Step 1: Add Custom Domain in Render
1. Go to your web service in Render dashboard
2. Click **Settings** → **Custom Domains**
3. Add your domain (e.g., `api.yourdomain.com`)

### Step 2: Configure DNS
Add a CNAME record:
```
api.yourdomain.com → your-app-name.onrender.com
```

### Step 3: Update Mailgun Webhook
```bash
curl -s --user 'api:YOUR_MAILGUN_API_KEY' \
  https://api.mailgun.net/v3/domains/YOUR_DOMAIN/webhooks \
  -F id='delivered' \
  -F url='https://api.yourdomain.com/api/email-agent/webhooks/mailgun'
```

## Security Best Practices

### Environment Variables
- **Never commit secrets** to your repository
- **Use Render's environment variable management**
- **Rotate keys regularly**

### HTTPS
- **Render provides free SSL** for all deployments
- **All webhook URLs use HTTPS** automatically

### Rate Limiting
The application includes built-in rate limiting:
- **100 webhook requests per minute**
- **50 task requests per minute**

## Troubleshooting

### Common Issues

#### 1. Deployment Fails
- **Check build logs** in Render dashboard
- **Verify Docker build** works locally:
  ```bash
  docker build -f deployment/Dockerfile .
  ```

#### 2. Webhook Not Received
- **Check webhook URL** in Mailgun dashboard
- **Verify signing key** matches environment variable
- **Check application logs** for webhook rejections

#### 3. Database Connection Issues
- **Verify DATABASE_URL** is set correctly
- **Check PostgreSQL service** is running
- **Review connection pool settings**

#### 4. High Memory Usage
- **Monitor Redis memory** usage
- **Check for memory leaks** in application logs
- **Consider upgrading plan** if needed

### Debug Mode

Enable debug logging temporarily:
1. **Add environment variable**: `LOG_LEVEL=DEBUG`
2. **Redeploy service**
3. **Monitor logs** for detailed information
4. **Remove debug mode** when done

### Performance Optimization

#### Upgrade Plans
For production workloads:
- **Database**: Upgrade from Starter to Standard
- **Web Service**: Use higher tier for better performance
- **Redis**: Consider managed Redis if needed

#### Scaling
```yaml
# In render.yaml for auto-scaling
scaling:
  minReplicas: 1
  maxReplicas: 3
  targetCPUPercent: 70
```

## Cost Optimization

### Free Tier Limits
- **Web Services**: Sleep after 15 minutes of inactivity
- **Database**: 90-day limit for free PostgreSQL
- **Bandwidth**: 100GB/month included

### Production Recommendations
- **Starter plan** for databases ($7/month)
- **Standard plan** for web services ($25/month)
- **Monitor usage** in dashboard

## Backup and Recovery

### Database Backups
Render automatically backs up PostgreSQL databases:
- **Daily backups** for 7 days
- **Point-in-time recovery** available

### Manual Backup
```bash
# Backup database
pg_dump $DATABASE_URL > backup.sql

# Restore (if needed)
psql $DATABASE_URL < backup.sql
```

## Support Resources

- **Render Documentation**: [render.com/docs](https://render.com/docs)
- **Render Community**: [community.render.com](https://community.render.com)
- **Status Page**: [status.render.com](https://status.render.com)

## Next Steps

1. **Set up monitoring** with external services (DataDog, New Relic)
2. **Configure alerting** for critical failures
3. **Implement CI/CD** for automated testing
4. **Add staging environment** for safe deployments
5. **Document runbooks** for operational procedures

---

## Quick Deployment Checklist

- [ ] Repository connected to Render
- [ ] Environment variables configured
- [ ] Services deployed successfully
- [ ] Health check passes
- [ ] Mailgun webhooks configured
- [ ] Test email processed successfully
- [ ] Monitoring set up
- [ ] Custom domain configured (optional)
- [ ] Team access configured
- [ ] Backup strategy documented

Your MCP Executive Platform should now be fully deployed on Render with public webhook endpoints accessible to Mailgun!

