# CI/CD and GitOps Notes

This project now supports a microservices shopping platform:

- `frontend`
- `user-api`
- `cart-api`
- `orders-api`
- `payment-api`
- `shipping-api`
- `redis`
- `mysql`

## Local Kind Build

For local Kind, build and load every service image:

```powershell
docker build -t orders-api:local .\app
docker build -t shopping-frontend:local -f .\services\frontend\Dockerfile .
docker build -t user-api:local -f .\services\user-api\Dockerfile .
docker build -t cart-api:local -f .\services\cart-api\Dockerfile .
docker build -t payment-api:local -f .\services\payment-api\Dockerfile .
docker build -t shipping-api:local -f .\services\shipping-api\Dockerfile .

kind load docker-image orders-api:local --name observability
kind load docker-image shopping-frontend:local --name observability
kind load docker-image user-api:local --name observability
kind load docker-image cart-api:local --name observability
kind load docker-image payment-api:local --name observability
kind load docker-image shipping-api:local --name observability
```

Deploy:

```powershell
kubectl apply -k .\k8s
```

## GitHub Actions CI/CD

The workflow is:

```text
.github/workflows/ci-cd.yml
```

It does:

1. Render Kubernetes manifests with `kubectl kustomize`.
2. Compile Python files.
3. Build all six service images.
4. Push images to GitHub Container Registry on `main` branch pushes.

## Argo CD Flow

Argo CD reads YAML from Git and deploys it.

For local Kind, keep using local image tags:

```text
orders-api:local
shopping-frontend:local
user-api:local
cart-api:local
payment-api:local
shipping-api:local
```

For a real cluster, update image names to registry images, for example:

```text
ghcr.io/shekar1221/orders-api:latest
ghcr.io/shekar1221/shopping-frontend:latest
```

Then commit and let Argo CD sync.

## Interview Explanation

Use this:

The project started as one service but was expanded into a microservices shopping platform. The frontend calls user, cart, orders, payment, and shipping APIs. Cart state is stored in Redis, while user data uses MySQL. Each service exposes `/metrics`, writes structured logs to stdout, and exports traces to the OpenTelemetry Collector. Prometheus scrapes all services, Loki and EFK collect logs, Jaeger shows traces, and Grafana provides dashboards. CI validates manifests and builds images, while Argo CD handles GitOps deployment and self-healing.
