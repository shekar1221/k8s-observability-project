#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="${1:-observability}"

echo "Building shopping platform images..."

docker build -t orders-api:local ./app
docker build -t shopping-frontend:local -f ./services/frontend/Dockerfile .
docker build -t user-api:local -f ./services/user-api/Dockerfile .
docker build -t cart-api:local -f ./services/cart-api/Dockerfile .
docker build -t payment-api:local -f ./services/payment-api/Dockerfile .
docker build -t shipping-api:local -f ./services/shipping-api/Dockerfile .

echo "Loading images into Kind cluster '${CLUSTER_NAME}'..."

kind load docker-image orders-api:local --name "${CLUSTER_NAME}"
kind load docker-image shopping-frontend:local --name "${CLUSTER_NAME}"
kind load docker-image user-api:local --name "${CLUSTER_NAME}"
kind load docker-image cart-api:local --name "${CLUSTER_NAME}"
kind load docker-image payment-api:local --name "${CLUSTER_NAME}"
kind load docker-image shipping-api:local --name "${CLUSTER_NAME}"

echo "Done. Apply manifests with: kubectl apply -k ./k8s"
