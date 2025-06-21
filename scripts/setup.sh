#!/bin/bash
# Setup script for Enhanced Oncall Agent

echo "🚀 Enhanced Oncall Agent Setup"
echo "=============================="
echo

# Check if GitHub MCP server exists
if [ -f "../github-mcp-server/github-mcp-server" ]; then
    echo "✅ GitHub MCP server found at ../github-mcp-server/"
else
    echo "📥 Downloading GitHub MCP server..."
    mkdir -p ../github-mcp-server
    cd ../github-mcp-server
    
    # Detect OS
    OS=$(uname -s)
    case "$OS" in
        Linux*)     
            URL="https://github.com/github/github-mcp-server/releases/latest/download/github-mcp-server-linux"
            ;;
        Darwin*)    
            URL="https://github.com/github/github-mcp-server/releases/latest/download/github-mcp-server-darwin"
            ;;
        MINGW*|CYGWIN*|MSYS*)     
            URL="https://github.com/github/github-mcp-server/releases/latest/download/github-mcp-server-windows.exe"
            ;;
        *)
            echo "❌ Unsupported OS: $OS"
            exit 1
            ;;
    esac
    
    curl -L -o github-mcp-server "$URL"
    chmod +x github-mcp-server
    cd -
    echo "✅ GitHub MCP server downloaded"
fi

# Check Python
echo
echo "🐍 Checking Python..."
if command -v python3 &> /dev/null; then
    echo "✅ Python3 found: $(python3 --version)"
else
    echo "❌ Python3 not found. Please install Python 3.11+"
    exit 1
fi

# Check Git
echo
echo "📁 Checking Git..."
if command -v git &> /dev/null; then
    echo "✅ Git found: $(git --version)"
else
    echo "❌ Git not found. Please install Git"
    exit 1
fi

# Create repository cache directory
echo
echo "📁 Creating repository cache directory..."
mkdir -p /tmp/oncall_repos
echo "✅ Cache directory ready: /tmp/oncall_repos"

# Check environment
echo
echo "🔧 Checking environment configuration..."
if [ -f ".env" ]; then
    echo "✅ .env file found"
else
    if [ -f ".env.example" ]; then
        echo "📝 Creating .env from .env.example"
        echo "⚠️  Please edit .env and add your API keys!"
        cp .env.example .env
    else
        echo "❌ No .env file found. Please create one with:"
        echo "   ANTHROPIC_API_KEY=your_key_here"
        echo "   GITHUB_TOKEN=your_token_here"
    fi
fi

echo
echo "🎉 Setup complete!"
echo
echo "Next steps:"
echo "1. Edit .env with your API keys"
echo "2. Install Python dependencies: pip install -r requirements.txt"
echo "3. Run the agent: python main.py"
echo
echo "Your agent is configured for:"
echo "✅ Complete repository access"
echo "✅ Offline operation capability"
echo "✅ Intelligent incident analysis"