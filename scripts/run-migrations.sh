#!/bin/bash
#
# Database Migration Runner for SWARM
# Runs Alembic migrations with proper environment setup
#

set -e  # Exit immediately if a command exits with a non-zero status

# Determine the absolute path to the project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ALEMBIC_DIR="$PROJECT_ROOT/migrations/alembic"
ALEMBIC_INI="$ALEMBIC_DIR/alembic.ini"

# Add project root to PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Load environment variables from .env files if they exist
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo "Loading environment variables from .env"
    set -a  # automatically export all variables
    source "$PROJECT_ROOT/.env"
    set +a
fi

# Check if DATABASE_URL is set, otherwise use default
if [ -z "$DATABASE_URL" ]; then
    echo "WARNING: DATABASE_URL not set, using default SQLite database"
    export DATABASE_URL="sqlite:///$PROJECT_ROOT/instance/mcp_executive.db"
fi

# Create instance directory if it doesn't exist (for SQLite)
if [[ "$DATABASE_URL" == sqlite* ]]; then
    SQLITE_DIR="$PROJECT_ROOT/instance"
    if [ ! -d "$SQLITE_DIR" ]; then
        echo "Creating SQLite database directory: $SQLITE_DIR"
        mkdir -p "$SQLITE_DIR"
    fi
fi

# Function to display usage information
show_usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  upgrade [revision]    Upgrade to the latest revision or specified revision"
    echo "  downgrade [revision]  Downgrade to the previous revision or specified revision"
    echo "  current               Show current revision"
    echo "  history               Show revision history"
    echo "  generate [message]    Generate a new migration (autogenerate)"
    echo "  stamp [revision]      Mark the database as being at a specific revision"
    echo "  init                  Initialize a new database and stamp it at head"
    echo ""
    echo "Options:"
    echo "  --help                Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 upgrade            # Upgrade to the latest revision"
    echo "  $0 upgrade +2         # Upgrade 2 revisions"
    echo "  $0 downgrade -1       # Downgrade 1 revision"
    echo "  $0 generate \"add user preferences\"  # Generate a new migration"
    echo ""
    echo "Environment:"
    echo "  DATABASE_URL          Database connection URL (default: SQLite)"
    echo "  ALEMBIC_CONFIG        Path to alembic.ini (default: $ALEMBIC_INI)"
}

# Check if Alembic is installed
if ! command -v alembic &> /dev/null; then
    echo "Error: Alembic is not installed. Please install it using:"
    echo "pip install alembic"
    exit 1
fi

# Check if alembic.ini exists
if [ ! -f "$ALEMBIC_INI" ]; then
    echo "Error: Alembic configuration file not found at $ALEMBIC_INI"
    echo "Please ensure the migrations directory is properly set up."
    exit 1
fi

# Process commands
case "$1" in
    upgrade)
        shift
        echo "Running database upgrade..."
        if [ -n "$1" ]; then
            alembic -c "$ALEMBIC_INI" upgrade "$1"
        else
            alembic -c "$ALEMBIC_INI" upgrade head
        fi
        echo "✅ Database upgrade completed"
        ;;
    
    downgrade)
        shift
        if [ -z "$1" ]; then
            echo "Error: Please specify a revision for downgrade (e.g., -1 or a revision ID)"
            exit 1
        fi
        
        echo "⚠️  WARNING: You are about to downgrade the database. This may result in data loss."
        read -p "Are you sure you want to continue? (y/N): " confirm
        if [[ "$confirm" != [yY] && "$confirm" != [yY][eE][sS] ]]; then
            echo "Downgrade cancelled."
            exit 0
        fi
        
        echo "Running database downgrade to $1..."
        alembic -c "$ALEMBIC_INI" downgrade "$1"
        echo "✅ Database downgrade completed"
        ;;
    
    current)
        echo "Current database revision:"
        alembic -c "$ALEMBIC_INI" current
        ;;
    
    history)
        echo "Database revision history:"
        alembic -c "$ALEMBIC_INI" history
        ;;
    
    generate)
        shift
        if [ -z "$1" ]; then
            echo "Error: Please provide a message for the migration"
            echo "Example: $0 generate \"add user preferences\""
            exit 1
        fi
        
        echo "Generating new migration: $1"
        alembic -c "$ALEMBIC_INI" revision --autogenerate -m "$1"
        echo "✅ Migration generated. Please review the generated script before committing."
        echo "   Location: $ALEMBIC_DIR/versions/"
        ;;
    
    stamp)
        shift
        if [ -z "$1" ]; then
            echo "Error: Please specify a revision for stamping (e.g., head or a revision ID)"
            exit 1
        fi
        
        echo "Stamping database as revision $1..."
        alembic -c "$ALEMBIC_INI" stamp "$1"
        echo "✅ Database stamped as revision $1"
        ;;
    
    init)
        echo "Initializing database and stamping as head..."
        
        # Check if the database already exists and has migrations
        current_rev=$(alembic -c "$ALEMBIC_INI" current 2>/dev/null || echo "")
        if [[ "$current_rev" == *"(head)"* ]]; then
            echo "Database is already initialized and up to date."
            exit 0
        fi
        
        # For SQLite, ensure the database file exists
        if [[ "$DATABASE_URL" == sqlite* ]]; then
            db_path=$(echo "$DATABASE_URL" | sed -E 's|sqlite:///(.+)|\1|')
            touch "$db_path"
        fi
        
        # Stamp the database as head
        alembic -c "$ALEMBIC_INI" stamp head
        echo "✅ Database initialized and stamped as head"
        ;;
    
    --help)
        show_usage
        ;;
    
    "")
        echo "Error: No command specified"
        show_usage
        exit 1
        ;;
    
    *)
        echo "Error: Unknown command '$1'"
        show_usage
        exit 1
        ;;
esac

exit 0
