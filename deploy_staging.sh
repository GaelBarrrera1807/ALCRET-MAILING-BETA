#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# deploy_staging.sh
# Pipeline de despliegue secuencial para el entorno Staging
# Industrial Prospecting AI Platform
#
# Uso:
#   1. Copiar .env.staging.template → .env.staging
#      y llenar las credenciales reales
#   2. chmod +x deploy_staging.sh
#   3. ./deploy_staging.sh
# ──────────────────────────────────────────────────────────────

set -o errexit
set -o pipefail
set -o nounset

COMPOSE_FILE="docker-compose.staging.yml"
ENV_FILE=".env.staging"

# ── Validación previa ──────────────────────────────────────

if [ ! -f "$ENV_FILE" ]; then
    echo "✗ ERROR: No se encuentra $ENV_FILE"
    echo "  Copia .env.staging.template → .env.staging"
    echo "  e inyecta las credenciales de staging."
    exit 1
fi

if grep -qi "CHANGE_ME" "$ENV_FILE"; then
    echo "✗ ERROR: $ENV_FILE contiene placeholders sin reemplazar."
    grep -n "CHANGE_ME" "$ENV_FILE"
    exit 1
fi

echo "✓ Validación de entorno superada"

# ── Pipeline secuencial ────────────────────────────────────

echo ""
echo "═══════════════════════════════════════════════"
echo " 1/4 — Pull de imágenes actualizadas"
echo "═══════════════════════════════════════════════"
docker-compose -f "$COMPOSE_FILE" pull

echo ""
echo "═══════════════════════════════════════════════"
echo " 2/4 — Migraciones de base de datos"
echo "       (incluye migration 0003 de leads)"
echo "═══════════════════════════════════════════════"
docker-compose -f "$COMPOSE_FILE" run --rm backend python manage.py migrate --noinput

echo ""
echo "═══════════════════════════════════════════════"
echo " 3/4 — Colecta de archivos estáticos"
echo "       (OpenAPI schema / Swagger UI)"
echo "═══════════════════════════════════════════════"
docker-compose -f "$COMPOSE_FILE" run --rm backend python manage.py collectstatic --noinput

echo ""
echo "═══════════════════════════════════════════════"
echo " 4/4 — Levantar servicios en segundo plano"
echo "═══════════════════════════════════════════════"
docker-compose -f "$COMPOSE_FILE" up -d

echo ""
echo "✓ Despliegue completado exitosamente"
echo "  Backend:  https://staging.api.industrialprospecting.com"
echo "  Frontend: https://staging.app.industrialprospecting.com"
echo "  Swagger:  https://staging.api.industrialprospecting.com/api/docs/"
