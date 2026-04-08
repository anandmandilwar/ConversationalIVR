#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../../env.sh"

REGION="${REGION:?ERROR: REGION not set in env.sh}"
ENVIRONMENT="${ENVIRONMENT:?ERROR: ENVIRONMENT not set in env.sh}"
TABLE_NAME="anycompany-ivr-client-config-${ENVIRONMENT}"
CLIENT_ID="CLIENT_001"
PHONE_NUMBER="${1:-}"

if [ -z "${PHONE_NUMBER}" ]; then
  echo "Usage: $0 <phone-number>"
  echo "  Example: $0 +18005551234"
  exit 1
fi

# Validate E.164 format
if [[ ! "${PHONE_NUMBER}" =~ ^\+[0-9]{10,15}$ ]]; then
  echo "❌ Invalid phone number: ${PHONE_NUMBER}"
  echo "   Must be E.164 format (e.g., +18005551234)"
  exit 1
fi

echo "Updating ${CLIENT_ID} phoneNumber → ${PHONE_NUMBER}"

aws dynamodb update-item \
  --table-name "${TABLE_NAME}" \
  --key '{"clientId": {"S": "'"${CLIENT_ID}"'"}}' \
  --update-expression "SET phoneNumber = :p, updatedAt = :u" \
  --expression-attribute-values '{
    ":p": {"S": "'"${PHONE_NUMBER}"'"},
    ":u": {"S": "'"$(date -u +%Y-%m-%dT%H:%M:%S.%6NZ)"'"}
  }' \
  --region "${REGION}" > /dev/null

echo "✅ Done! Verifying..."

aws dynamodb get-item \
  --table-name "${TABLE_NAME}" \
  --key '{"clientId": {"S": "'"${CLIENT_ID}"'"}}' \
  --projection-expression "clientId, phoneNumber, updatedAt" \
  --region "${REGION}" \
  --output table
