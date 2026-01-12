#!/bin/bash
# scripts/generate-secrets.sh

set -euo pipefail

# Determine script directory to locate secrets folder relative to it
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SECRETS_DIR="${PROJECT_ROOT}/secrets"

mkdir -p "$SECRETS_DIR"
chmod 700 "$SECRETS_DIR"

echo "Generating secure API keys..."

# Generate cryptographically secure API keys
# Uses openssl if available, otherwise falls back to /dev/urandom
if command -v openssl &> /dev/null; then
    VLLM_API_KEY=$(openssl rand -hex 32)
    LLAMACPP_API_KEY=$(openssl rand -hex 32)
    ADMIN_KEY=$(openssl rand -hex 48)
else
    VLLM_API_KEY=$(cat /dev/urandom | tr -dc 'a-f0-9' | fold -w 64 | head -n 1)
    LLAMACPP_API_KEY=$(cat /dev/urandom | tr -dc 'a-f0-9' | fold -w 64 | head -n 1)
    ADMIN_KEY=$(cat /dev/urandom | tr -dc 'a-f0-9' | fold -w 96 | head -n 1)
fi

KEY_FILE="$SECRETS_DIR/api-keys.env"

# Store in secure file
cat > "$KEY_FILE" << EOF
# Generated: $(date -Iseconds)
# DO NOT COMMIT TO VERSION CONTROL
VLLM_API_KEY=${VLLM_API_KEY}
LLAMACPP_API_KEY=${LLAMACPP_API_KEY}
ADMIN_KEY=${ADMIN_KEY}
EOF

chmod 600 "$KEY_FILE"

echo "✓ API keys generated and stored in $KEY_FILE"
echo "✓ Ensure docker-compose.yml contains: env_file: ./secrets/api-keys.env"
