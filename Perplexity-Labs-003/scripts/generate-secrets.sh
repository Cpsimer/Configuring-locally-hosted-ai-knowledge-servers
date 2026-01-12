#!/bin/bash
# ~/ai-idp/scripts/generate-secrets.sh
# Generate cryptographically secure API keys for AI IDP
# Version: 1.0 | Date: 2026-01-12

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_DIR="${SCRIPT_DIR}/../secrets"

echo "=== AI IDP Secure Key Generation ==="
echo ""

# Create secrets directory with restricted permissions
mkdir -p "$SECRETS_DIR"
chmod 700 "$SECRETS_DIR"

# Check if keys already exist
if [ -f "$SECRETS_DIR/api-keys.env" ]; then
    echo "⚠️  API keys already exist at: $SECRETS_DIR/api-keys.env"
    read -p "Regenerate keys? This will invalidate existing tokens. (y/N): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo "Keeping existing keys."
        exit 0
    fi
    # Backup existing keys
    cp "$SECRETS_DIR/api-keys.env" "$SECRETS_DIR/api-keys.env.bak.$(date +%s)"
    echo "✓ Backed up existing keys"
fi

# Generate cryptographically secure API keys
echo "Generating secure API keys..."

VLLM_API_KEY=$(openssl rand -hex 32)
LLAMACPP_API_KEY=$(openssl rand -hex 32)
ADMIN_KEY=$(openssl rand -hex 48)

# Store in secure file
cat > "$SECRETS_DIR/api-keys.env" << EOF
# AI IDP API Keys
# Generated: $(date -Iseconds)
# DO NOT COMMIT TO VERSION CONTROL
# Regenerate with: ./scripts/generate-secrets.sh

VLLM_API_KEY=${VLLM_API_KEY}
LLAMACPP_API_KEY=${LLAMACPP_API_KEY}
ADMIN_KEY=${ADMIN_KEY}
EOF

# Secure the file
chmod 600 "$SECRETS_DIR/api-keys.env"

# Create .gitignore if it doesn't exist
if [ ! -f "$SECRETS_DIR/.gitignore" ]; then
    echo "*" > "$SECRETS_DIR/.gitignore"
    echo "!.gitignore" >> "$SECRETS_DIR/.gitignore"
fi

echo ""
echo "✓ API keys generated successfully!"
echo "✓ Stored in: $SECRETS_DIR/api-keys.env"
echo "✓ Permissions: $(stat -c '%a' "$SECRETS_DIR/api-keys.env") (read/write for owner only)"
echo ""
echo "Usage in docker-compose.yml:"
echo "  env_file:"
echo "    - ./secrets/api-keys.env"
echo ""
echo "To use VLLM_API_KEY in requests:"
echo "  curl -H \"Authorization: Bearer \${VLLM_API_KEY}\" http://localhost:8000/v1/models"
echo ""

# Display first 8 chars of each key for verification
echo "Key verification (first 8 chars):"
echo "  VLLM_API_KEY:     ${VLLM_API_KEY:0:8}..."
echo "  LLAMACPP_API_KEY: ${LLAMACPP_API_KEY:0:8}..."
echo "  ADMIN_KEY:        ${ADMIN_KEY:0:8}..."
