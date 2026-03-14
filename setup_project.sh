#!/bin/bash

# ============================================
# Isha Return Gifts - Complete Setup Script
# Run: bash setup_project.sh
# ============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
GOLD='\033[0;33m'
NC='\033[0m'

echo ""
echo -e "${GOLD}╔════════════════════════════════════════════╗${NC}"
echo -e "${GOLD}║     🎁 Isha Return Gifts - Setup Script    ║${NC}"
echo -e "${GOLD}║     Database: SQLite (Zero Setup)          ║${NC}"
echo -e "${GOLD}╚════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Check Python
echo -e "${BLUE}[1/6] Checking Python...${NC}"
if command -v python3 &>/dev/null; then
    PYTHON=python3
    echo -e "${GREEN}✅ $(python3 --version)${NC}"
elif command -v python &>/dev/null; then
    PYTHON=python
    echo -e "${GREEN}✅ $(python --version)${NC}"
else
    echo -e "${RED}❌ Python not found. Install Python 3.10+ from python.org${NC}"
    exit 1
fi

# Step 2: Create venv
echo ""
echo -e "${BLUE}[2/6] Creating virtual environment...${NC}"
if [ -d "venv" ]; then
    echo -e "${YELLOW}⚠️  venv already exists — skipping.${NC}"
else
    $PYTHON -m venv venv
    echo -e "${GREEN}✅ venv created${NC}"
fi

# Step 3: Activate venv
echo ""
echo -e "${BLUE}[3/6] Activating virtual environment...${NC}"
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OS" == "Windows_NT" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi
echo -e "${GREEN}✅ venv activated — $(which python)${NC}"

# Step 4: Install packages
echo ""
echo -e "${BLUE}[4/6] Installing packages...${NC}"
pip install --upgrade pip --quiet
pip install -r requirements.txt
echo -e "${GREEN}✅ Packages installed${NC}"

# Step 5: Migrations
echo ""
echo -e "${BLUE}[5/6] Running database migrations...${NC}"
python manage.py makemigrations products 2>/dev/null || true
python manage.py makemigrations orders 2>/dev/null || true
python manage.py makemigrations payments 2>/dev/null || true
python manage.py makemigrations users 2>/dev/null || true
python manage.py makemigrations 2>/dev/null || true
python manage.py migrate
echo -e "${GREEN}✅ Migrations done${NC}"

# Step 6: Seed data
echo ""
echo -e "${BLUE}[6/6] Creating admin user and sample data...${NC}"
python setup.py

# Done
echo ""
echo -e "${GOLD}╔════════════════════════════════════════════╗${NC}"
echo -e "${GOLD}║          ✅ Setup Complete!                ║${NC}"
echo -e "${GOLD}╚════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${GREEN}Website:      ${NC}http://127.0.0.1:8000/"
echo -e "  ${GREEN}Dashboard:    ${NC}http://127.0.0.1:8000/dashboard/"
echo -e "  ${GREEN}Django Admin: ${NC}http://127.0.0.1:8000/admin/"
echo ""
echo -e "  ${YELLOW}Login: admin / admin@12345${NC}"
echo ""
echo -e "${BLUE}▶  Next time, just run:${NC}"
echo -e "   ${YELLOW}source venv/bin/activate && python manage.py runserver${NC}"
echo ""
echo -e "${GOLD}📧 To enable email: Edit settings.py and add your Gmail + App Password${NC}"
echo -e "${GOLD}💳 To enable Razorpay: Add your API keys in settings.py${NC}"
echo ""
