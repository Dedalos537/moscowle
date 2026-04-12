#!/bin/bash

###############################################################################
# VERIFICATION SCRIPT - CHECK PROJECT BEFORE PRODUCTION BUILD
# Ensures all necessary files and dependencies are present
###############################################################################

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

errors=0
warnings=0

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🔍 MOSCOWLE IA MVP - PRE-PRODUCTION VERIFICATION${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo ""

# Check critical files
echo -e "${BLUE}[1/5] Checking critical files...${NC}"
critical_files=("config.py" "run.py" "passenger_wsgi.py" "requirements.txt" "app/__init__.py")

for file in "${critical_files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "  ${GREEN}✓${NC} $file"
    else
        echo -e "  ${RED}✗${NC} $file (MISSING)"
        ((errors++))
    fi
done

# Check directories
echo ""
echo -e "${BLUE}[2/5] Checking directories...${NC}"
dirs=("app/routes" "app/services" "app/templates" "app/static")

for dir in "${dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "  ${GREEN}✓${NC} $dir"
    else
        echo -e "  ${RED}✗${NC} $dir (MISSING)"
        ((errors++))
    fi
done

# Check models file
if [ -f "app/models.py" ]; then
    echo -e "  ${GREEN}✓${NC} app/models.py"
else
    echo -e "  ${RED}✗${NC} app/models.py (MISSING)"
    ((errors++))
fi

# Check Python version
echo ""
echo -e "${BLUE}[3/5] Checking Python version...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "  ${GREEN}✓${NC} Python3 detected: $PYTHON_VERSION"
else
    echo -e "  ${RED}✗${NC} Python3 not found"
    ((errors++))
fi

# Check Git repo
echo ""
echo -e "${BLUE}[4/5] Checking project metadata...${NC}"
if [ -d ".git" ]; then
    echo -e "  ${GREEN}✓${NC} Git repository present"
    COMMIT=$(git log -1 --pretty=format:"%H" 2>/dev/null || echo "N/A")
    echo -e "    Latest commit: ${COMMIT:0:8}"
else
    echo -e "  ${YELLOW}!${NC} Git repository not found (optional)"
    ((warnings++))
fi

# Check environment
echo ""
echo -e "${BLUE}[5/5] Checking environment...${NC}"
if [ -f ".env" ]; then
    echo -e "  ${GREEN}✓${NC} .env file exists"
    SECRET_KEY=$(grep "^SECRET_KEY=" .env | head -1)
    if [ -z "$SECRET_KEY" ]; then
        echo -e "    ${YELLOW}!${NC} WARNING: SECRET_KEY not set in .env"
        ((warnings++))
    fi
else
    echo -e "  ${YELLOW}!${NC} .env file not found (will use .env.example)"
    ((warnings++))
fi

# Summary
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}📊 VERIFICATION SUMMARY${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo ""

if [ $errors -eq 0 ] && [ $warnings -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed! Ready to build.${NC}"
    exit 0
elif [ $errors -eq 0 ]; then
    echo -e "${YELLOW}⚠️  $warnings warning(s). You can proceed, but review above.${NC}"
    exit 0
else
    echo -e "${RED}❌ $errors error(s) found. Fix them before proceeding.${NC}"
    exit 1
fi
