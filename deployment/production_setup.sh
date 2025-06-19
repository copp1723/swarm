#!/bin/bash
#
# SWARM Multi-Agent System Production Setup Script
# ===============================================
#
# This script sets up a production environment for the SWARM multi-agent system.
# It installs all dependencies, configures services, and secures the server.
#
# Usage: sudo ./production_setup.sh [domain] [email]
#   - domain: Your domain name (e.g., swarm.example.com)
#   - email: Email for Let's Encrypt notifications
#
# Example: sudo ./production_setup.sh swarm.example.com admin@example.com
#
# Note: This script must be run as root or with sudo privileges.
#

set -e  # Exit immediately if a command exits with non-zero status

# Colors for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration variables
SWARM_USER="swarm"
SWARM_HOME="/home/$SWARM_USER"
SWARM_APP="$SWARM_HOME/swarm"
SWARM_LOGS="$SWARM_HOME/logs"
SWARM_DATA="$SWARM_HOME/data"
PYTHON_VERSION="3.11"
NODE_VERSION="18"
POSTGRES_VERSION="15"
DOMAIN=${1:-"localhost"}
EMAIL=${2:-"admin@example.com"}
APP_PORT="5006"  # Default Flask port for SWARM

# Check if script is run as root
if [ "$(id -u)" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root or with sudo privileges.${NC}"
    exit 1
fi

# Function to print section headers
section() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a package is installed
package_installed() {
    dpkg -l "$1" >/dev/null 2>&1
}

# Function to check if a service is active
service_active() {
    systemctl is-active --quiet "$1"
}

section "System Update and Basic Packages"
apt-get update
apt-get upgrade -y
apt-get install -y \
    build-essential \
    curl \
    wget \
    git \
    unzip \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    supervisor \
    fail2ban \
    ufw \
    logrotate

section "Installing Python $PYTHON_VERSION"
if ! command_exists "python$PYTHON_VERSION"; then
    add-apt-repository -y ppa:deadsnakes/ppa
    apt-get update
    apt-get install -y \
        "python$PYTHON_VERSION" \
        "python$PYTHON_VERSION-dev" \
        "python$PYTHON_VERSION-venv" \
        "python$PYTHON_VERSION-distutils"
    
    # Set Python 3.11 as default python3
    update-alternatives --install /usr/bin/python3 python3 "/usr/bin/python$PYTHON_VERSION" 1
    update-alternatives --set python3 "/usr/bin/python$PYTHON_VERSION"
    
    # Install pip for Python 3.11
    curl -sS https://bootstrap.pypa.io/get-pip.py | python$PYTHON_VERSION
    
    echo -e "${GREEN}Python $PYTHON_VERSION installed successfully.${NC}"
else
    echo -e "${YELLOW}Python $PYTHON_VERSION is already installed.${NC}"
fi

section "Installing PostgreSQL $POSTGRES_VERSION"
if ! package_installed "postgresql-$POSTGRES_VERSION"; then
    # Add PostgreSQL repository
    echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list
    wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
    apt-get update
    
    # Install PostgreSQL
    apt-get install -y "postgresql-$POSTGRES_VERSION" "postgresql-contrib-$POSTGRES_VERSION" libpq-dev
    
    # Start and enable PostgreSQL service
    systemctl start postgresql
    systemctl enable postgresql
    
    # Create database and user
    sudo -u postgres psql -c "CREATE USER $SWARM_USER WITH PASSWORD 'swarm_password';"
    sudo -u postgres psql -c "CREATE DATABASE swarm_db OWNER $SWARM_USER;"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE swarm_db TO $SWARM_USER;"
    
    echo -e "${GREEN}PostgreSQL $POSTGRES_VERSION installed and configured successfully.${NC}"
else
    echo -e "${YELLOW}PostgreSQL is already installed.${NC}"
fi

section "Installing Redis"
if ! package_installed "redis-server"; then
    apt-get install -y redis-server
    
    # Configure Redis to use systemd
    sed -i 's/supervised no/supervised systemd/g' /etc/redis/redis.conf
    
    # Start and enable Redis service
    systemctl restart redis-server
    systemctl enable redis-server
    
    echo -e "${GREEN}Redis installed and configured successfully.${NC}"
else
    echo -e "${YELLOW}Redis is already installed.${NC}"
fi

section "Installing Node.js $NODE_VERSION"
if ! command_exists "node"; then
    # Install Node.js
    curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash -
    apt-get install -y nodejs
    
    # Install yarn
    npm install -g yarn
    
    echo -e "${GREEN}Node.js $NODE_VERSION installed successfully.${NC}"
else
    echo -e "${YELLOW}Node.js is already installed: $(node -v)${NC}"
fi

section "Installing Nginx"
if ! package_installed "nginx"; then
    apt-get install -y nginx
    
    # Start and enable Nginx service
    systemctl start nginx
    systemctl enable nginx
    
    echo -e "${GREEN}Nginx installed successfully.${NC}"
else
    echo -e "${YELLOW}Nginx is already installed.${NC}"
fi

section "Creating SWARM User and Directories"
# Create swarm user if it doesn't exist
if ! id "$SWARM_USER" &>/dev/null; then
    useradd -m -s /bin/bash "$SWARM_USER"
    echo -e "${GREEN}User $SWARM_USER created successfully.${NC}"
else
    echo -e "${YELLOW}User $SWARM_USER already exists.${NC}"
fi

# Create necessary directories
mkdir -p "$SWARM_APP"
mkdir -p "$SWARM_LOGS"
mkdir -p "$SWARM_DATA"
mkdir -p "$SWARM_DATA/uploads"
mkdir -p "$SWARM_DATA/instance"

# Set proper ownership and permissions
chown -R "$SWARM_USER:$SWARM_USER" "$SWARM_HOME"
chmod -R 755 "$SWARM_HOME"

echo -e "${GREEN}SWARM directories created and permissions set.${NC}"

section "Setting Up Python Virtual Environment"
# Create and activate virtual environment
if [ ! -d "$SWARM_HOME/venv" ]; then
    sudo -u "$SWARM_USER" python$PYTHON_VERSION -m venv "$SWARM_HOME/venv"
    echo -e "${GREEN}Python virtual environment created.${NC}"
else
    echo -e "${YELLOW}Python virtual environment already exists.${NC}"
fi

# Install basic Python packages
sudo -u "$SWARM_USER" "$SWARM_HOME/venv/bin/pip" install --upgrade pip wheel setuptools
sudo -u "$SWARM_USER" "$SWARM_HOME/venv/bin/pip" install gunicorn uvicorn[standard] supervisor

section "Configuring Systemd Services"
# Create systemd service for SWARM
cat > /etc/systemd/system/swarm.service << EOF
[Unit]
Description=SWARM Multi-Agent System
After=network.target postgresql.service redis-server.service

[Service]
User=$SWARM_USER
Group=$SWARM_USER
WorkingDirectory=$SWARM_APP
Environment="PATH=$SWARM_HOME/venv/bin"
ExecStart=$SWARM_HOME/venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:$APP_PORT app:app
Restart=always
RestartSec=5
StartLimitInterval=0

[Install]
WantedBy=multi-user.target
EOF

# Create systemd service for Celery worker
cat > /etc/systemd/system/swarm-celery.service << EOF
[Unit]
Description=SWARM Celery Worker
After=network.target postgresql.service redis-server.service

[Service]
User=$SWARM_USER
Group=$SWARM_USER
WorkingDirectory=$SWARM_APP
Environment="PATH=$SWARM_HOME/venv/bin"
ExecStart=$SWARM_HOME/venv/bin/celery -A app.celery worker --loglevel=info
Restart=always
RestartSec=5
StartLimitInterval=0

[Install]
WantedBy=multi-user.target
EOF

# Create systemd service for Celery beat (scheduler)
cat > /etc/systemd/system/swarm-celery-beat.service << EOF
[Unit]
Description=SWARM Celery Beat
After=network.target postgresql.service redis-server.service

[Service]
User=$SWARM_USER
Group=$SWARM_USER
WorkingDirectory=$SWARM_APP
Environment="PATH=$SWARM_HOME/venv/bin"
ExecStart=$SWARM_HOME/venv/bin/celery -A app.celery beat --loglevel=info
Restart=always
RestartSec=5
StartLimitInterval=0

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd to recognize new services
systemctl daemon-reload

echo -e "${GREEN}Systemd services created.${NC}"

section "Configuring Nginx"
# Create Nginx site configuration
cat > /etc/nginx/sites-available/swarm << EOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:$APP_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }

    location /static {
        alias $SWARM_APP/static;
        expires 30d;
    }

    location /uploads {
        alias $SWARM_DATA/uploads;
        internal;
    }

    client_max_body_size 50M;
}
EOF

# Enable the site
if [ -f /etc/nginx/sites-enabled/default ]; then
    rm /etc/nginx/sites-enabled/default
fi

if [ ! -L /etc/nginx/sites-enabled/swarm ]; then
    ln -s /etc/nginx/sites-available/swarm /etc/nginx/sites-enabled/
fi

# Test Nginx configuration
nginx -t

# Reload Nginx to apply changes
systemctl reload nginx

echo -e "${GREEN}Nginx configured for SWARM.${NC}"

section "Configuring Firewall"
# Configure UFW
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw allow 5006/tcp  # Allow direct access to Flask app (optional)
ufw --force enable

echo -e "${GREEN}Firewall configured.${NC}"

section "Setting Up SSL with Let's Encrypt"
if [ "$DOMAIN" != "localhost" ]; then
    # Install Certbot
    apt-get install -y certbot python3-certbot-nginx
    
    # Obtain SSL certificate
    certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL" --redirect
    
    # Auto-renew certificates
    echo "0 3 * * * root certbot renew --quiet" > /etc/cron.d/certbot-renew
    
    echo -e "${GREEN}SSL certificate installed for $DOMAIN.${NC}"
else
    echo -e "${YELLOW}Skipping SSL setup as domain is set to localhost.${NC}"
fi

section "Creating Production .env Template"
cat > "$SWARM_APP/.env.production" << EOF
# SWARM Multi-Agent System Production Environment Configuration

# OpenRouter API Configuration
OPENROUTER_API_KEY=your_openrouter_api_key_here

# SWARM API Configuration
SWARM_DEV_API_KEY=your_production_api_key_here
ALLOW_DEV_API_KEY=false

# Database Configuration
DATABASE_URL=postgresql://$SWARM_USER:swarm_password@localhost/swarm_db

# Email Service Configuration (Mailgun)
MAILGUN_API_KEY=your_mailgun_api_key_here
MAILGUN_DOMAIN=your_mailgun_domain_here
MAILGUN_SIGNING_KEY=your_mailgun_webhook_signing_key_here

# Supermemory Integration
SUPERMEMORY_BASE_URL=https://api.supermemory.ai/v3
SUPERMEMORY_API_KEY=your_supermemory_api_key_here

# GitHub Integration (Optional)
GITHUB_PAT=your_github_personal_access_token_here

# Redis Configuration (for Celery)
REDIS_URL=redis://localhost:6379/0

# Security Settings
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)

# Flask Configuration
FLASK_ENV=production
FLASK_DEBUG=0

# Logging
LOG_LEVEL=INFO
LOG_FILE=$SWARM_LOGS/swarm.log

# MCP Filesystem Configuration
MCP_FILESYSTEM_ALLOWED_DIRS=$SWARM_APP,$SWARM_DATA
MCP_FILESYSTEM_ALLOW_WRITE=true
MCP_FILESYSTEM_ALLOW_DELETE=false

# Feature Flags
ENABLE_AUTO_DISPATCH=true
ENABLE_REALTIME_UPDATES=true
ENABLE_AUDIT_LOGGING=true

# Performance Settings
RATE_LIMIT_WEBHOOKS_PER_MINUTE=100
RATE_LIMIT_TASKS_PER_MINUTE=50
WEBHOOK_PROCESSING_TIMEOUT=30
TASK_DISPATCH_TIMEOUT=60

# Sentry Error Tracking (Optional)
SENTRY_DSN=your_sentry_dsn_here
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
EOF

# Set proper ownership
chown "$SWARM_USER:$SWARM_USER" "$SWARM_APP/.env.production"
chmod 600 "$SWARM_APP/.env.production"

echo -e "${GREEN}Production .env template created.${NC}"

section "Setting Up Log Rotation"
cat > /etc/logrotate.d/swarm << EOF
$SWARM_LOGS/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 $SWARM_USER $SWARM_USER
    sharedscripts
    postrotate
        systemctl reload swarm.service >/dev/null 2>&1 || true
    endscript
}
EOF

echo -e "${GREEN}Log rotation configured.${NC}"

section "Securing the Server"
# Configure fail2ban
cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true

[nginx-http-auth]
enabled = true
EOF

# Restart fail2ban
systemctl restart fail2ban

# Set secure permissions for sensitive files
chmod 750 "$SWARM_HOME"
chmod -R 700 "$SWARM_APP/.env.production"

echo -e "${GREEN}Server security hardened.${NC}"

section "Installation Complete"
echo -e "${GREEN}SWARM production environment setup completed successfully!${NC}"
echo -e "\nNext steps:"
echo -e "1. Deploy your SWARM application code to ${YELLOW}$SWARM_APP${NC}"
echo -e "2. Edit ${YELLOW}$SWARM_APP/.env.production${NC} with your actual API keys"
echo -e "3. Install application dependencies: ${YELLOW}$SWARM_HOME/venv/bin/pip install -r $SWARM_APP/requirements.txt${NC}"
echo -e "4. Initialize the database: ${YELLOW}cd $SWARM_APP && $SWARM_HOME/venv/bin/python init/init_database.py${NC}"
echo -e "5. Start the services:"
echo -e "   ${YELLOW}sudo systemctl start swarm.service${NC}"
echo -e "   ${YELLOW}sudo systemctl start swarm-celery.service${NC}"
echo -e "   ${YELLOW}sudo systemctl start swarm-celery-beat.service${NC}"
echo -e "\nTo check service status:"
echo -e "${YELLOW}sudo systemctl status swarm.service${NC}"
echo -e "\nYour SWARM application will be available at: ${BLUE}https://$DOMAIN${NC}"
