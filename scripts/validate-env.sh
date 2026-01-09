#!/bin/bash
# Production environment validation script
# Run this before deploying to ensure all required environment variables are set

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "Production Environment Validation"
echo "========================================"
echo ""

ERRORS=0
WARNINGS=0

# Required environment variables
REQUIRED_VARS=(
    "JWT_SECRET"
    "CSRF_SECRET"
    "ENCRYPTION_KEY"
    "OPENROUTER_API_KEY"
    "SOLANA_RPC_URL"
    "SOLANA_TREASURY_ADDRESS"
    "RUNNER_SHARED_SECRET"
    "POSTGRES_PASSWORD"
)

# Check required variables
echo "Checking required environment variables..."
echo ""

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo -e "  ${RED}[MISSING]${NC} $var"
        ERRORS=$((ERRORS + 1))
    else
        # Check minimum length for secrets
        val="${!var}"
        len=${#val}

        case $var in
            JWT_SECRET|CSRF_SECRET|RUNNER_SHARED_SECRET)
                if [ $len -lt 32 ]; then
                    echo -e "  ${RED}[WEAK]${NC} $var must be at least 32 characters (currently $len)"
                    ERRORS=$((ERRORS + 1))
                else
                    echo -e "  ${GREEN}[OK]${NC} $var (${len} chars)"
                fi
                ;;
            ENCRYPTION_KEY)
                if [ $len -lt 32 ]; then
                    echo -e "  ${RED}[WEAK]${NC} $var must be a valid Fernet key"
                    ERRORS=$((ERRORS + 1))
                else
                    echo -e "  ${GREEN}[OK]${NC} $var"
                fi
                ;;
            POSTGRES_PASSWORD)
                if [ $len -lt 16 ]; then
                    echo -e "  ${YELLOW}[WARN]${NC} $var should be at least 16 characters"
                    WARNINGS=$((WARNINGS + 1))
                else
                    echo -e "  ${GREEN}[OK]${NC} $var"
                fi
                ;;
            SOLANA_TREASURY_ADDRESS)
                if [ $len -lt 32 ] || [ $len -gt 44 ]; then
                    echo -e "  ${RED}[INVALID]${NC} $var doesn't look like a valid Solana address"
                    ERRORS=$((ERRORS + 1))
                else
                    echo -e "  ${GREEN}[OK]${NC} $var"
                fi
                ;;
            *)
                echo -e "  ${GREEN}[OK]${NC} $var"
                ;;
        esac
    fi
done

echo ""

# Optional but recommended variables
echo "Checking optional environment variables..."
echo ""

OPTIONAL_VARS=(
    "APP_BASE_URL"
    "API_BASE_URL"
    "LOG_LEVEL"
    "PRICING_MIN_SOL"
    "PRICING_MAX_SOL"
    "DEFAULT_PRICE_SOL"
)

for var in "${OPTIONAL_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo -e "  ${YELLOW}[DEFAULT]${NC} $var (using default value)"
    else
        echo -e "  ${GREEN}[SET]${NC} $var = ${!var}"
    fi
done

echo ""

# Production-specific checks
echo "Running production checks..."
echo ""

# Check DEBUG mode
if [ "$DEBUG" = "true" ] || [ "$DEBUG" = "1" ]; then
    echo -e "  ${YELLOW}[WARN]${NC} DEBUG mode is enabled - disable for production"
    WARNINGS=$((WARNINGS + 1))
else
    echo -e "  ${GREEN}[OK]${NC} DEBUG mode is disabled"
fi

# Check if using localhost URLs
if [[ "$APP_BASE_URL" == *"localhost"* ]] || [[ "$API_BASE_URL" == *"localhost"* ]]; then
    echo -e "  ${YELLOW}[WARN]${NC} Using localhost URLs - set proper domain for production"
    WARNINGS=$((WARNINGS + 1))
else
    echo -e "  ${GREEN}[OK]${NC} URLs are not using localhost"
fi

# Check HTTPS
if [[ "$APP_BASE_URL" == "https://"* ]]; then
    echo -e "  ${GREEN}[OK]${NC} APP_BASE_URL uses HTTPS"
else
    echo -e "  ${YELLOW}[WARN]${NC} APP_BASE_URL should use HTTPS in production"
    WARNINGS=$((WARNINGS + 1))
fi

echo ""
echo "========================================"

if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}Validation FAILED: $ERRORS error(s), $WARNINGS warning(s)${NC}"
    echo "Fix the errors above before deploying."
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}Validation PASSED with $WARNINGS warning(s)${NC}"
    echo "Review warnings above before deploying."
    exit 0
else
    echo -e "${GREEN}Validation PASSED${NC}"
    echo "Environment is ready for production."
    exit 0
fi
