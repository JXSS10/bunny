#!/bin/bash

# Colors for terminal output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color
CYAN='\033[0;36m'

# Function to print banner
print_banner() {
    clear
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════╗"
    echo "║     BunnyCDN Downloader Setup        ║"
    echo "║          by MrGadhvii                ║"
    echo "╚══════════════════════════════════════╝"
    echo -e "${NC}"
}

print_banner

# Detect environment
if [[ "$OSTYPE" == "msys" ]]; then
    echo -e "${BLUE}Detected Git Bash environment${NC}"
    # For Git Bash, we use 'py' or 'python' command
    if command -v py &> /dev/null; then
        PYTHON_CMD="py"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo -e "${RED}Python not found! Please install Python from python.org${NC}"
        exit 1
    fi
elif [ -e $PREFIX/bin/pkg ]; then  # Termux
    echo -e "${BLUE}Detected Termux environment${NC}"
    pkg update -y
    pkg install -y python wget curl
    PYTHON_CMD="python"
else  # Linux/Mac
    echo -e "${BLUE}Detected Unix-like environment${NC}"
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo -e "${RED}Python not found!${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}Using Python command: $PYTHON_CMD${NC}"

# Install requirements
echo -e "${BLUE}Installing Python packages...${NC}"
$PYTHON_CMD -m pip install -r requirements.txt
if [ $? -eq 0 ]; then
    echo -e "${GREEN}All dependencies installed successfully!${NC}"
    sleep 2
else
    echo -e "${RED}Failed to install Python packages!${NC}"
    exit 1
fi

# Clear screen and start the application
clear
echo -e "${GREEN}Starting BunnyCDN Downloader...${NC}"
sleep 1
clear

# Run the application
$PYTHON_CMD start.py 