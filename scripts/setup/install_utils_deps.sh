#!/bin/bash
# Install utility module dependencies

echo "Installing utility module dependencies..."

# Check if we're in a virtual environment
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "Virtual environment detected: $VIRTUAL_ENV"
    pip install jsonschema pyyaml
else
    echo "No virtual environment active. Attempting to activate venv..."
    if [ -d "venv" ]; then
        source venv/bin/activate
        pip install jsonschema pyyaml
    else
        echo "Warning: No virtual environment found. Installing globally (requires sudo):"
        echo "sudo pip3 install jsonschema pyyaml"
        echo ""
        echo "Or create a virtual environment first:"
        echo "python3 -m venv venv"
        echo "source venv/bin/activate"
        echo "pip install -r requirements.txt"
    fi
fi

echo "Done!"