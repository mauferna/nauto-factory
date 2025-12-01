#!/bin/bash

# Network Automation Factory - Setup Script
# Automates installation and configuration

set -e  # Exit on error

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║        NETWORK AUTOMATION FACTORY - SETUP                    ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Error: Python 3.10 or higher is required"
    echo "   Current version: $python_version"
    exit 1
fi

echo "✅ Python version: $python_version"
echo ""

# Check for pip
echo "Checking for pip..."
if ! command -v pip3 &> /dev/null; then
    echo "❌ Error: pip3 not found"
    exit 1
fi
echo "✅ pip3 found"
echo ""

# Create virtual environment (optional but recommended)
read -p "Create virtual environment? (recommended) [Y/n]: " create_venv
create_venv=${create_venv:-Y}

if [[ $create_venv =~ ^[Yy]$ ]]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "✅ Virtual environment created and activated"
    echo ""
fi

# Install dependencies
echo "Installing dependencies..."
pip3 install --upgrade pip
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Error installing dependencies"
    exit 1
fi
echo ""

# Create necessary directories
echo "Creating project directories..."
mkdir -p output/{playbooks,tests,cicd,docs,reviews}
mkdir -p logs
mkdir -p memory
echo "✅ Directories created"
echo ""

# Check for API key
echo "Checking for Google AI API key..."
if [ -z "$GOOGLE_API_KEY" ]; then
    echo "⚠️  GOOGLE_API_KEY environment variable not set"
    echo ""
    read -p "Enter your Google AI API key (or press Enter to set later): " api_key
    
    if [ -n "$api_key" ]; then
        export GOOGLE_API_KEY="$api_key"
        echo "export GOOGLE_API_KEY=\"$api_key\"" >> ~/.bashrc
        echo "✅ API key set and saved to ~/.bashrc"
    else
        echo "⚠️  You can set it later with:"
        echo "   export GOOGLE_API_KEY='your-api-key'"
    fi
else
    echo "✅ API key found"
fi
echo ""

# Run tests (optional)
read -p "Run test suite? [Y/n]: " run_tests
run_tests=${run_tests:-Y}

if [[ $run_tests =~ ^[Yy]$ ]]; then
    echo "Running tests..."
    pytest tests/ -v
    echo ""
fi

# Verify installation
echo "Verifying installation..."
if python3 -c "import google.generativeai; import yaml; import ansible" 2>/dev/null; then
    echo "✅ All core dependencies verified"
else
    echo "⚠️  Some dependencies may be missing"
fi
echo ""

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║                    SETUP COMPLETE!                           ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo ""
echo "1. If you created a virtual environment, activate it:"
echo "   source venv/bin/activate"
echo ""
echo "2. If you haven't set your API key yet:"
echo "   export GOOGLE_API_KEY='your-api-key'"
echo ""
echo "3. Run your first automation:"
echo "   python main.py --spec examples/example_spec.yaml"
echo ""
echo "4. View the quick start guide:"
echo "   cat QUICKSTART.md"
echo ""
echo "Happy automating! 🚀"
echo ""
