#!/bin/bash
# ~/ai-idp/scripts/generate-secrets.sh
# OWASP 2025 Compliant Secret Generation
# Version: 2.0 | Date: 2026-01-12

set -euo pipefail

# Configuration
SECRETS_DIR="${HOME}/ai-idp/secrets"
PROJECT_DIR="${HOME}/ai-idp"
ROTATION_DAYS=90

echo "============================================="
echo "AI IDP Cryptographic Secret Generator v2.0"
echo "OWASP 2025 Compliant"
echo "============================================="

# Create secure directories
mkdir -p "$SECRETS_DIR"
chmod 700 "$SECRETS_DIR"

# Verify openssl is available
if ! command -v openssl &> /dev/null; then
    echo "ERROR: openssl is required but not installed."
    exit 1
fi

# Generate cryptographically secure API keys (256-bit entropy minimum)
echo "Generating cryptographically secure API keys..."

VLLM_API_KEY=$(openssl rand -hex 32)           # 256-bit
LLAMACPP_API_KEY=$(openssl rand -hex 32)        # 256-bit
ADMIN_KEY=$(openssl rand -hex 48)               # 384-bit for admin operations
ROTATION_TOKEN=$(openssl rand -hex 16)          # For key rotation validation

# Calculate next rotation date
NEXT_ROTATION=$(date -d "+${ROTATION_DAYS} days" +"%Y-%m-%d")

# Create secure environment file
cat > "$SECRETS_DIR/api-keys.env" <<EOF
# AI IDP API Keys - Cryptographically Generated
# Generated: $(date -Iseconds)
# Next Rotation: ${NEXT_ROTATION}
# 
# SECURITY WARNINGS:
# - DO NOT commit to version control
# - DO NOT share in plain text
# - Rotate every ${ROTATION_DAYS} days
# - Store backup in encrypted vault

VLLM_API_KEY=${VLLM_API_KEY}
LLAMACPP_API_KEY=${LLAMACPP_API_KEY}
ADMIN_KEY=${ADMIN_KEY}
ROTATION_TOKEN=${ROTATION_TOKEN}
KEY_GENERATED_AT=$(date +%s)
KEY_ROTATION_DATE=${NEXT_ROTATION}
EOF

# Set restrictive permissions
chmod 600 "$SECRETS_DIR/api-keys.env"

# Create .gitignore to prevent accidental commit
cat > "$PROJECT_DIR/.gitignore" <<EOF
# AI IDP Security - DO NOT MODIFY
secrets/
*.env
*.key
*.pem
.env*
api-keys*
*.secret

# Docker
.docker/

# Logs
logs/
*.log

# Cache
.cache/
__pycache__/
*.pyc
EOF

# Create secrets README for documentation
cat > "$SECRETS_DIR/README.md" <<EOF
# AI IDP Secrets Directory

## Security Protocol

This directory contains cryptographically generated API keys for the AI IDP system.

### Key Rotation Schedule
- **Current rotation period**: ${ROTATION_DAYS} days
- **Next rotation date**: ${NEXT_ROTATION}
- **Rotation token**: Use to verify key updates

### Files
- \`api-keys.env\` - Docker environment file with API keys
- \`README.md\` - This file

### Rotation Procedure
1. Run: \`./scripts/generate-secrets.sh\`
2. Restart containers: \`docker-compose down && docker-compose up -d\`
3. Verify health: \`curl -H "Authorization: Bearer \$VLLM_API_KEY" http://localhost:8000/health\`

### Emergency Revocation
To immediately revoke all keys:
\`\`\`bash
rm -f ~/ai-idp/secrets/api-keys.env
docker-compose down
./scripts/generate-secrets.sh
docker-compose up -d
\`\`\`

### Backup Location
Store encrypted backup at: [CONFIGURE_YOUR_SECURE_LOCATION]
EOF

chmod 644 "$SECRETS_DIR/README.md"

# Verification
echo ""
echo "============================================="
echo "✅ API Keys Generated Successfully"
echo "============================================="
echo ""
echo "Location:    $SECRETS_DIR/api-keys.env"
echo "Permissions: $(stat -c %a "$SECRETS_DIR/api-keys.env")"
echo "Next Rotation: $NEXT_ROTATION"
echo ""
echo "Keys generated (first 8 chars shown):"
echo "  VLLM_API_KEY:     ${VLLM_API_KEY:0:8}..."
echo "  LLAMACPP_API_KEY: ${LLAMACPP_API_KEY:0:8}..."
echo "  ADMIN_KEY:        ${ADMIN_KEY:0:8}..."
echo ""
echo "============================================="
echo "Next Steps:"
echo "============================================="
echo "1. Add to docker-compose.yml:"
echo "   env_file:"
echo "     - ./secrets/api-keys.env"
echo ""
echo "2. Test vLLM authentication:"
echo "   source $SECRETS_DIR/api-keys.env"
echo "   curl -H \"Authorization: Bearer \$VLLM_API_KEY\" http://localhost:8000/health"
echo ""
echo "3. Store backup in secure location (encrypted)"
echo ""
echo "⚠️  WARNING: Never commit secrets/ directory to git!"
