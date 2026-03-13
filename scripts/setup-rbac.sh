#!/usr/bin/env bash
# setup-rbac.sh — One-time RBAC provisioning for Opal Container Apps.
# Run locally with Owner/User Access Administrator permissions:
#   az login
#   bash scripts/setup-rbac.sh [--env dev]
set -euo pipefail

ENV_NAME="${1:-dev}"
[[ "$ENV_NAME" == "--env" ]] && ENV_NAME="${2:-dev}"
RG_NAME="opal-${ENV_NAME}-rg"

echo "=== Opal RBAC Setup (env: ${ENV_NAME}, rg: ${RG_NAME}) ==="

# Discover infrastructure
ACR_NAME=$(az acr list -g "${RG_NAME}" --query "[0].name" -o tsv)
ACR_ID=$(az acr show -n "${ACR_NAME}" -g "${RG_NAME}" --query "id" -o tsv)

STORAGE=$(az storage account list -g "${RG_NAME}" --query "[0].name" -o tsv)
STORAGE_ID=$(az storage account show -g "${RG_NAME}" -n "${STORAGE}" --query "id" -o tsv)

SB=$(az servicebus namespace list -g "${RG_NAME}" --query "[0].name" -o tsv)
SB_ID=$(az servicebus namespace show -g "${RG_NAME}" -n "${SB}" --query id -o tsv)

echo "ACR:     ${ACR_NAME} (${ACR_ID})"
echo "Storage: ${STORAGE} (${STORAGE_ID})"
echo "SB:      ${SB} (${SB_ID})"
echo ""

# Active Container Apps (v0.4 — unified pipeline worker replaces old per-step workers)
APPS=(
  "opal-web-api-${ENV_NAME}"
  "opal-billing-service-${ENV_NAME}"
  "opal-pipeline-worker-${ENV_NAME}"
  "opal-export-worker-${ENV_NAME}"
)

# Apps that only need AcrPull (no storage or service bus access)
ACR_ONLY_APPS=(
  "opal-shopify-app-${ENV_NAME}"
)

# Legacy workers (deactivated — kept for rollback)
# "opal-orchestrator-${ENV_NAME}"
# "opal-bg-removal-worker-${ENV_NAME}"
# "opal-scene-worker-${ENV_NAME}"
# "opal-upscale-worker-${ENV_NAME}"

# Role → scope pairs for each app
ROLES=(
  "AcrPull|${ACR_ID}"
  "Storage Blob Data Contributor|${STORAGE_ID}"
  "Storage Blob Delegator|${STORAGE_ID}"
  "Azure Service Bus Data Receiver|${SB_ID}"
  "Azure Service Bus Data Sender|${SB_ID}"
)

TOTAL=0
CREATED=0
EXISTED=0
FAILED=0

for APP in "${APPS[@]}"; do
  PID=$(az containerapp show -g "${RG_NAME}" -n "${APP}" --query "identity.principalId" -o tsv 2>/dev/null || echo "")
  if [ -z "${PID}" ]; then
    echo "WARNING: ${APP} has no system identity — skipping (ensure app exists first)"
    continue
  fi
  echo "--- ${APP} (principal: ${PID})"

  for ENTRY in "${ROLES[@]}"; do
    ROLE="${ENTRY%%|*}"
    SCOPE="${ENTRY##*|}"
    TOTAL=$((TOTAL + 1))

    COUNT=$(az role assignment list \
      --scope "${SCOPE}" \
      --query "[?principalId=='${PID}' && roleDefinitionName=='${ROLE}'] | length(@)" \
      -o tsv 2>/dev/null || echo "0")

    if [ "${COUNT:-0}" -gt 0 ]; then
      echo "  ✓ ${ROLE} (exists)"
      EXISTED=$((EXISTED + 1))
    else
      echo "  + Assigning ${ROLE}..."
      if az role assignment create \
        --assignee-object-id "${PID}" \
        --assignee-principal-type ServicePrincipal \
        --role "${ROLE}" \
        --scope "${SCOPE}" -o none 2>&1; then
        CREATED=$((CREATED + 1))
      else
        echo "  ✗ FAILED to assign ${ROLE}"
        FAILED=$((FAILED + 1))
      fi
    fi
  done
  echo ""
done

# ACR-only apps (e.g., Shopify app — no storage or service bus needed)
for APP in "${ACR_ONLY_APPS[@]}"; do
  PID=$(az containerapp show -g "${RG_NAME}" -n "${APP}" --query "identity.principalId" -o tsv 2>/dev/null || echo "")
  if [ -z "${PID}" ]; then
    echo "WARNING: ${APP} has no system identity — skipping (ensure app exists first)"
    continue
  fi
  echo "--- ${APP} (principal: ${PID}) [AcrPull only]"

  TOTAL=$((TOTAL + 1))
  COUNT=$(az role assignment list \
    --scope "${ACR_ID}" \
    --query "[?principalId=='${PID}' && roleDefinitionName=='AcrPull'] | length(@)" \
    -o tsv 2>/dev/null || echo "0")

  if [ "${COUNT:-0}" -gt 0 ]; then
    echo "  ✓ AcrPull (exists)"
    EXISTED=$((EXISTED + 1))
  else
    echo "  + Assigning AcrPull..."
    if az role assignment create \
      --assignee-object-id "${PID}" \
      --assignee-principal-type ServicePrincipal \
      --role "AcrPull" \
      --scope "${ACR_ID}" -o none 2>&1; then
      CREATED=$((CREATED + 1))
    else
      echo "  ✗ FAILED to assign AcrPull"
      FAILED=$((FAILED + 1))
    fi
  fi
  echo ""
done

echo "=== Summary ==="
echo "Total checked: ${TOTAL}"
echo "Already existed: ${EXISTED}"
echo "Newly created: ${CREATED}"
echo "Failed: ${FAILED}"

if [ "${FAILED}" -gt 0 ]; then
  echo "ERROR: ${FAILED} role assignment(s) failed. Do you have Owner or User Access Administrator on the resource group?"
  exit 1
fi

echo "All RBAC roles are in place."
