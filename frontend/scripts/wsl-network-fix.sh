#!/bin/bash

echo "🔧 WSL Network Fix for PostgreSQL Connections"
echo "============================================"
echo ""

# Check if running in WSL
if ! grep -qi microsoft /proc/version; then
    echo "❌ Not running in WSL. This script is for WSL only."
    exit 1
fi

echo "Current WSL network configuration:"
echo ""

# Show current network info
echo "1. WSL IP Address:"
ip addr show eth0 | grep inet | awk '{print "   " $2}'
echo ""

echo "2. Windows Host IP:"
cat /etc/resolv.conf | grep nameserver | awk '{print "   " $2}'
echo ""

echo "3. Current iptables rules:"
sudo iptables -L OUTPUT -n | head -5
echo ""

echo "📋 Possible Solutions:"
echo ""

echo "Solution 1: Use WSL2 networking mode"
echo "   In PowerShell (as Administrator):"
echo "   wsl --set-version <distro-name> 2"
echo ""

echo "Solution 2: Disable WSL firewall for testing"
echo "   sudo iptables -P OUTPUT ACCEPT"
echo "   sudo iptables -F OUTPUT"
echo ""

echo "Solution 3: Add explicit allow rule for PostgreSQL"
echo "   sudo iptables -A OUTPUT -p tcp --dport 5432 -j ACCEPT"
echo ""

echo "Solution 4: Use Windows host networking (temporary)"
echo "   export http_proxy=http://$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):8888"
echo "   export https_proxy=http://$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):8888"
echo ""

echo "Solution 5: Reset WSL networking"
echo "   In PowerShell:"
echo "   wsl --shutdown"
echo "   netsh winsock reset"
echo "   netsh int ip reset all"
echo "   netsh winhttp reset proxy"
echo "   Then restart WSL"
echo ""

echo "Would you like to try Solution 3 (add PostgreSQL allow rule)? [y/N]"
read -r response

if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo "Adding iptables rule..."
    sudo iptables -A OUTPUT -p tcp --dport 5432 -j ACCEPT
    sudo iptables -A OUTPUT -p tcp --dport 443 -j ACCEPT
    echo "✅ Rules added. Try the connection test again."
else
    echo "Skipping automatic fix. Try one of the solutions above manually."
fi