#!/usr/bin/env bash
# helpers.sh — Shared helper functions for Opal CI/CD workflow.
# Sourced by build-deploy-dev.yml steps.
#
# Required env vars (set by workflow before sourcing):
#   RG_NAME, ACR_ID, ACR_LOGIN, STORAGE, SB_ID, CAE
#
# Optional env vars:
#   ENV_VARS — bash array of env vars for app creation
#   PLACEHOLDER_IMAGE — fallback image for new apps

PLACEHOLDER_IMAGE="${PLACEHOLDER_IMAGE:-mcr.microsoft.com/azuredocs/containerapps-helloworld:latest}"

ensure_identity () {
  local NAME="$1"
  local PID
  PID=$(az containerapp show -g "${RG_NAME}" -n "${NAME}" --query "identity.principalId" -o tsv 2>/dev/null || echo "")
  if [ -n "${PID}" ]; then
    echo "Identity already exists for ${NAME}: ${PID}"
    return 0
  fi
  az containerapp identity assign -g "${RG_NAME}" -n "${NAME}" --system-assigned >/dev/null || true
  for i in $(seq 1 12); do
    PID=$(az containerapp show -g "${RG_NAME}" -n "${NAME}" --query "identity.principalId" -o tsv 2>/dev/null || echo "")
    if [ -n "${PID}" ]; then
      echo "Identity confirmed for ${NAME}: ${PID}"
      return 0
    fi
    echo "  Waiting for identity on ${NAME} (${i}/12)..."
    sleep 5
  done
  echo "ERROR: System identity not confirmed for ${NAME} after 60s"
  return 1
}

verify_roles () {
  local NAME="$1"
  local PID
  PID=$(az containerapp show -g "${RG_NAME}" -n "${NAME}" --query "identity.principalId" -o tsv)
  [ -n "${PID}" ] || { echo "ERROR: No principalId for ${NAME}"; return 1; }

  local STORAGE_ID
  STORAGE_ID=$(az storage account show -g "${RG_NAME}" -n "${STORAGE}" --query id -o tsv)

  local ALL_OK=true
  local ROLES=(
    "AcrPull|${ACR_ID}"
    "Storage Blob Data Contributor|${STORAGE_ID}"
    "Storage Blob Delegator|${STORAGE_ID}"
    "Azure Service Bus Data Receiver|${SB_ID}"
    "Azure Service Bus Data Sender|${SB_ID}"
  )

  for ENTRY in "${ROLES[@]}"; do
    local ROLE="${ENTRY%%|*}"
    local SCOPE="${ENTRY##*|}"
    local COUNT
    COUNT=$(az role assignment list \
      --scope "${SCOPE}" \
      --query "[?principalId=='${PID}' && roleDefinitionName=='${ROLE}'] | length(@)" \
      -o tsv 2>/dev/null || echo "0")
    if [ "${COUNT:-0}" -gt 0 ]; then
      echo "  ✓ ${ROLE}"
    else
      echo "  ✗ MISSING: ${ROLE}"
      ALL_OK=false
    fi
  done

  if [ "${ALL_OK}" != "true" ]; then
    echo ""
    echo "ERROR: ${NAME} is missing required RBAC roles."
    echo "Run locally with Owner permissions:  bash scripts/setup-rbac.sh"
    return 1
  fi
}

ensure_registry_binding () {
  local NAME="$1"
  local EXISTING
  EXISTING=$(az containerapp show -g "${RG_NAME}" -n "${NAME}" \
    --query "properties.configuration.registries[?server=='${ACR_LOGIN}'].identity | [0]" \
    -o tsv 2>/dev/null || echo "")
  if [ "${EXISTING}" = "system" ] || [ "${EXISTING}" = "SystemAssigned" ]; then
    echo "Registry already bound for ${NAME}"
    return 0
  fi
  echo "Binding registry for ${NAME}..."
  for attempt in 1 2 3; do
    az containerapp registry set -g "${RG_NAME}" -n "${NAME}" \
      --server "${ACR_LOGIN}" --identity system >/dev/null 2>&1 || true
    sleep 15
    STATE=$(az containerapp show -g "${RG_NAME}" -n "${NAME}" \
      --query "properties.provisioningState" -o tsv 2>/dev/null || echo "Unknown")
    if [ "${STATE}" != "Failed" ]; then
      echo "Registry bound for ${NAME} (state: ${STATE})"
      return 0
    fi
    echo "  Registry binding attempt ${attempt}/3 left app in Failed state; waiting 30s before retry..."
    sleep 30
  done
  echo "WARNING: Registry binding unstable after 3 attempts — proceeding (deploy_image will validate)"
}

wait_for_acr_pull () {
  local NAME="$1"
  local PID
  PID=$(az containerapp show -g "${RG_NAME}" -n "${NAME}" --query "identity.principalId" -o tsv)
  COUNT=$(az role assignment list \
    --scope "${ACR_ID}" \
    --query "[?principalId=='${PID}' && roleDefinitionName=='AcrPull'] | length(@)" \
    -o tsv 2>/dev/null || echo "0")
  if [ "${COUNT:-0}" -gt 0 ]; then
    echo "AcrPull already confirmed for ${NAME} — skipping wait"
    return 0
  fi
  echo "Polling until AcrPull is visible in ARM for ${NAME} (max 2 min)..."
  for i in $(seq 1 12); do
    COUNT=$(az role assignment list \
      --scope "${ACR_ID}" \
      --query "[?principalId=='${PID}' && roleDefinitionName=='AcrPull'] | length(@)" \
      -o tsv 2>/dev/null || echo "0")
    if [ "${COUNT:-0}" -gt 0 ]; then
      echo "AcrPull confirmed in ARM (attempt ${i}). Waiting 10s for enforcement..."
      sleep 10
      return 0
    fi
    echo "  AcrPull not yet visible (${i}/12), waiting 10s..."
    sleep 10
  done
  echo "WARNING: AcrPull not confirmed after 2 min — proceeding anyway"
}

ensure_ingress () {
  local NAME="$1"
  local MODE="$2"   # external|internal|none
  local PORT="$3"

  if [ "${MODE}" = "none" ]; then
    return 0
  fi

  az containerapp ingress enable -g "${RG_NAME}" -n "${NAME}" \
    --type "${MODE}" \
    --target-port "${PORT}" \
    --transport auto >/dev/null 2>&1 || true
  sleep 5

  az containerapp ingress update -g "${RG_NAME}" -n "${NAME}" \
    --type "${MODE}" \
    --target-port "${PORT}" >/dev/null 2>&1 || true
  sleep 5
}

ensure_app_exists () {
  local NAME="$1"
  local INGRESS="$2"
  local PORT="$3"

  if az containerapp show -g "${RG_NAME}" -n "${NAME}" >/dev/null 2>&1; then
    STATE=$(az containerapp show -g "${RG_NAME}" -n "${NAME}" --query "properties.provisioningState" -o tsv || true)
    echo "App exists: ${NAME} (state: ${STATE})"
    if [ "${STATE}" = "Failed" ]; then
      echo "App is Failed -> deleting so it can be recreated cleanly..."
      az containerapp delete -g "${RG_NAME}" -n "${NAME}" --yes
    fi
  fi

  if ! az containerapp show -g "${RG_NAME}" -n "${NAME}" >/dev/null 2>&1; then
    echo "Creating ${NAME} with placeholder image..."
    az containerapp create -g "${RG_NAME}" -n "${NAME}" \
      --environment "${CAE}" \
      --image "${PLACEHOLDER_IMAGE}" \
      --min-replicas 1 --max-replicas 3 \
      --env-vars "${ENV_VARS[@]}" >/dev/null
    sleep 5
  fi

  ensure_identity "${NAME}"

  # Verify RBAC roles exist (read-only — does not create them)
  echo "Verifying RBAC for ${NAME}..."
  verify_roles "${NAME}"

  # ACR pull must be confirmed before registry binding
  wait_for_acr_pull "${NAME}"
  ensure_registry_binding "${NAME}"

  ensure_ingress "${NAME}" "${INGRESS}" "${PORT}"
}
