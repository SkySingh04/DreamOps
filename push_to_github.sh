#!/bin/bash
# Script to help push to GitHub with authentication

echo "🚀 GitHub Push Helper for oncall-agent"
echo "====================================="
echo
echo "This script will help you push to: https://github.com/SkySingh04/oncall-agent.git"
echo
echo "You need a GitHub Personal Access Token (PAT)"
echo "Get one from: https://github.com/settings/tokens/new"
echo "Required scopes: ✅ repo (all)"
echo
read -p "Enter your GitHub username (or press Enter for 'SkySingh04'): " username
username=${username:-SkySingh04}

echo
echo "Enter your GitHub Personal Access Token:"
echo "(It will be hidden as you type)"
read -s token
echo

if [ -z "$token" ]; then
    echo "❌ Error: Token cannot be empty"
    exit 1
fi

echo
echo "📤 Pushing to GitHub..."
echo

# Push with credentials
git push https://${username}:${token}@github.com/SkySingh04/oncall-agent.git main

if [ $? -eq 0 ]; then
    echo
    echo "✅ Push successful!"
    echo "Your enhanced oncall agent with GitHub MCP integration is now on GitHub!"
else
    echo
    echo "❌ Push failed. Please check your token and try again."
fi