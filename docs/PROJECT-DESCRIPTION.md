# Project Description: Kubernetes Shopping App With Argo CD and Observability

This document explains the complete project from a beginner point of view.

Use it for:

- Understanding the full project flow
- Explaining the project in interviews
- Remembering what each module does
- Troubleshooting common Kubernetes, Argo CD, Docker, Python, and observability issues

## 1. Project In One Sentence

This project deploys a Python Flask microservices shopping application on Kubernetes, manages it using Argo CD GitOps, packages services with Docker, and monitors the platform using Prometheus, Grafana, Loki, Elasticsearch, Kibana, OpenTelemetry, and Jaeger.

## 2. High-Level Interview Explanation

You can say:

```text
I built a Kubernetes observability project around a microservices shopping platform.
The application has a frontend and multiple backend APIs for users, cart, orders,
payments, and shipping. Each service is written in Python Flask and containerized
with Docker. The services run on a local Kind Kubernetes cluster.

For GitOps, I used Argo CD to deploy the Kubernetes manifests from Git. The manifests
are organized with Kustomize. Argo CD continuously compares the desired state in Git
with the live cluster and can self-heal drift.

For observability, every service exposes Prometheus metrics, writes logs to stdout,
and exports traces using OpenTelemetry. Prometheus collects metrics, Grafana displays
dashboards, Loki and Elasticsearch collect logs, Kibana searches Elasticsearch logs,
and Jaeger shows distributed traces.
```

## 3. Main Architecture

```text
Developer
  |
  | pushes code and Kubernetes YAML
  v
Git repository
  |
  | Argo CD watches repo
  v
Argo CD Application
  |
  | syncs k8s/ manifests
  v
Kind Kubernetes cluster
  |
  +--> NGINX Ingress
  |      |
  |      +--> frontend
  |              |
  |              +--> user-api --> MySQL
  |              +--> cart-api --> Redis
  |              +--> orders-api
  |              +--> payment-api
  |              +--> shipping-api
  |
  +--> Prometheus --> Grafana
  +--> Promtail --> Loki --> Grafana
  +--> Fluent Bit --> Elasticsearch --> Kibana
  +--> OpenTelemetry Collector --> Jaeger
```

## 4. Start From Argo CD

Argo CD is the GitOps part of this project.

### What Argo CD Does

Argo CD reads Kubernetes YAML from Git and applies it to the cluster.

In this project, the Argo CD application is:

```text
argocd/applications/observability-app.yaml
```

Important configuration:

```yaml
source:
  repoURL: https://github.com/shekar1221/k8s-observability-project.git
  targetRevision: main
  path: k8s
destination:
  server: https://kubernetes.default.svc
  namespace: observability-demo
syncPolicy:
  automated:
    prune: true
    selfHeal: true
```

Meaning:

| Field | Meaning |
|---|---|
| `repoURL` | Git repo where the Kubernetes manifests live |
| `targetRevision` | Git branch Argo CD watches |
| `path: k8s` | Folder Argo CD deploys |
| `namespace` | Kubernetes namespace where app resources go |
| `prune: true` | Delete live resources removed from Git |
| `selfHeal: true` | Fix manual cluster changes and return to Git state |

### Beginner Mental Model

```text
Git is the source of truth.
Argo CD reads Git.
Kubernetes runs what Argo CD applies.
If someone changes the cluster manually, Argo CD can detect and fix drift.
```

### Important Kind Note

Argo CD deploys Kubernetes YAML. It does not build Docker images.

For a local Kind cluster, you must build and load local images first:

```powershell
.\scripts\build-load-kind.ps1
```

Then Argo CD can deploy the YAML that references images like:

```text
orders-api:local
shopping-frontend:local
user-api:local
cart-api:local
payment-api:local
shipping-api:local
```

In a real cluster, these image names should point to a registry such as GitHub Container Registry, Amazon ECR, Docker Hub, or Azure Container Registry.

## 5. Argo CD Setup Steps

### Step 1: Install Argo CD

```powershell
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl wait --for=condition=available deployment/argocd-server -n argocd --timeout=300s
```

### Step 2: Open Argo CD UI

```powershell
kubectl port-forward svc/argocd-server -n argocd 8081:443
```

Open:

```text
https://localhost:8081
```

Username:

```text
admin
```

Get password:

```powershell
[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String((kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath="{.data.password}")))
```

### Step 3: Deploy The Project Using Argo CD

```powershell
kubectl apply -f .\argocd\applications\observability-app.yaml
```

Check the Argo CD application:

```powershell
kubectl get applications -n argocd
```

Expected:

```text
observability-stack   Synced   Healthy
```

### Step 4: Explain This In Interview

You can say:

```text
I used Argo CD as the GitOps controller. The Argo CD Application points to the
k8s folder in my Git repository. That folder contains the Kustomize base for the
application and observability stack. Argo CD syncs those manifests to the
observability-demo namespace. I enabled automated sync, prune, and self-heal so
the cluster stays aligned with Git.
```

## 6. CI/CD Flow

This project also includes a GitHub Actions workflow:

```text
.github/workflows/ci-cd.yml
```

The workflow has three main jobs.

### Validate Job

It does:

- Renders Kubernetes manifests using `kubectl kustomize k8s`
- Checks Python syntax using `python -m py_compile`

### Security Scan Job

It does:

- Kubernetes schema validation using kubeconform
- Repository and manifest scanning using Trivy
- IaC scanning using Checkov
- Secret scanning using Gitleaks
- Dockerfile linting using Hadolint
- Python SAST using Bandit
- Python dependency audit using pip-audit

### Build Job

It builds these images:

| Service | Dockerfile |
|---|---|
| `orders-api` | `app/Dockerfile` |
| `shopping-frontend` | `services/frontend/Dockerfile` |
| `user-api` | `services/user-api/Dockerfile` |
| `cart-api` | `services/cart-api/Dockerfile` |
| `payment-api` | `services/payment-api/Dockerfile` |
| `shipping-api` | `services/shipping-api/Dockerfile` |

On push to `main`, it can push images to GitHub Container Registry.

### CI/CD vs GitOps

| Area | Tool | Responsibility |
|---|---|---|
| CI | GitHub Actions | Validate, scan, build, push images |
| CD/GitOps | Argo CD | Deploy Kubernetes YAML from Git |
| Runtime | Kubernetes | Run the containers |
| Observability | Grafana, Prometheus, Loki, Kibana, Jaeger | Monitor and troubleshoot |

## 7. Kubernetes Deployment Structure

The main Kubernetes folder is:

```text
k8s/
```

It is managed by:

```text
k8s/kustomization.yaml
```

The Kustomize file includes:

| File | Purpose |
|---|---|
| `00-namespace.yaml` | Creates `observability-demo` namespace |
| `10-jaeger.yaml` | Deploys Jaeger for traces |
| `20-otel-collector.yaml` | Deploys OpenTelemetry Collector |
| `30-efk.yaml` | Deploys Elasticsearch, Fluent Bit, Kibana |
| `40-app.yaml` | Deploys `orders-api` |
| `45-platform-data.yaml` | Deploys MySQL and Redis |
| `46-shopping-services.yaml` | Deploys frontend, user, cart, payment, shipping |
| `50-prometheus.yaml` | Deploys Prometheus |
| `60-loki-promtail.yaml` | Deploys Loki and Promtail |
| `70-grafana.yaml` | Deploys Grafana with data sources and dashboard |
| `80-ingress.yaml` | Creates browser hostnames through NGINX ingress |

Apply everything manually with:

```powershell
kubectl apply -k .\k8s
```

Or let Argo CD apply it from Git.

## 8. Local Kind Cluster

Kind runs a Kubernetes cluster inside Docker.

The cluster config is:

```text
kind-config.yaml
```

Important settings:

```yaml
name: observability
extraPortMappings:
  - containerPort: 80
    hostPort: 80
  - containerPort: 443
    hostPort: 443
```

This maps your local machine ports `80` and `443` to the Kind cluster. That is why browser URLs like this work:

```text
http://shop.observability.local
```

Create the cluster:

```powershell
kind create cluster --config .\kind-config.yaml
```

Install NGINX ingress:

```powershell
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.11.1/deploy/static/provider/kind/deploy.yaml
kubectl wait --namespace ingress-nginx --for=condition=ready pod --selector=app.kubernetes.io/component=controller --timeout=180s
```

Build and load images:

```powershell
.\scripts\build-load-kind.ps1
```

Deploy:

```powershell
kubectl apply -k .\k8s
```

One-command local setup:

```powershell
.\scripts\start-kind-full.ps1
```

## 9. Hostnames And Ingress

The ingress file is:

```text
k8s/80-ingress.yaml
```

It maps friendly hostnames to Kubernetes services.

| Hostname | Service |
|---|---|
| `shop.observability.local` | `frontend` |
| `orders.observability.local` | `orders-api` |
| `cart.observability.local` | `cart-api` |
| `users.observability.local` | `user-api` |
| `payment.observability.local` | `payment-api` |
| `shipping.observability.local` | `shipping-api` |
| `grafana.observability.local` | `grafana` |
| `prometheus.observability.local` | `prometheus` |
| `jaeger.observability.local` | `jaeger` |
| `kibana.observability.local` | `kibana` |
| `loki.observability.local` | `loki` |

Windows hosts file entries are stored in:

```text
scripts/hosts-entries.txt
```

Add them to:

```text
C:\Windows\System32\drivers\etc\hosts
```

Then run:

```powershell
ipconfig /flushdns
```

## 10. Application Modules

This project is a shopping platform.

### Module Summary

| Module | Type | Purpose | Data Store |
|---|---|---|---|
| `frontend` | Web app | User interface and checkout flow | Calls APIs |
| `orders-api` | Backend API | Products, orders, demo metrics | In memory |
| `user-api` | Backend API | User data | MySQL with in-memory fallback |
| `cart-api` | Backend API | Cart add/remove/clear | Redis with in-memory fallback |
| `payment-api` | Backend API | Demo payment authorization | In memory |
| `shipping-api` | Backend API | Demo shipment creation | In memory |
| `mysql` | Database | User-style relational storage | MySQL |
| `redis` | Cache/data store | Cart persistence | Redis |

## 11. Frontend Module

Folder:

```text
services/frontend/
```

Important files:

| File | Purpose |
|---|---|
| `services/frontend/app.py` | Flask frontend application |
| `services/frontend/templates/index.html` | HTML page |
| `services/frontend/static/styles.css` | CSS styling |
| `services/frontend/Dockerfile` | Builds frontend Docker image |

The frontend is a Python Flask app. It renders the shopping website using Jinja templates.

Main features:

- Logo and header
- Product cards
- Cart panel
- Add to cart
- Remove cart item
- Clear cart
- Checkout
- Service status panel
- Links to Grafana, Prometheus, Jaeger, Kibana, and Loki
- Links to backend API routes

Important routes:

| Route | Purpose |
|---|---|
| `GET /` | Main shopping web page |
| `GET /home` | JSON summary for frontend state |
| `POST /cart/items` | Add item to cart |
| `POST /cart/remove` | Remove item from cart |
| `POST /cart/clear` | Clear cart |
| `POST /checkout` | Run checkout through payment and shipping APIs |
| `GET /checkout-demo` | Generate demo traffic for observability |
| `GET /metrics` | Prometheus metrics |
| `GET /healthz` | Kubernetes health check |

The frontend calls backend services using Kubernetes service DNS:

```text
http://user-api:8080
http://cart-api:8080
http://orders-api:8080
http://payment-api:8080
http://shipping-api:8080
```

### Frontend Interview Explanation

```text
The frontend is a Flask web application. It renders an HTML storefront using
Jinja templates and CSS. It does not directly store data. It calls backend
services through Kubernetes service names. For example, adding an item calls
cart-api, checkout calls payment-api and shipping-api, and product listing comes
from orders-api.
```

## 12. Backend Modules

### orders-api

Folder:

```text
app/
```

Purpose:

- Product catalog
- Orders endpoint
- Demo cart endpoints
- Prometheus metrics
- OpenTelemetry spans
- Structured logs

Important routes:

| Route | Purpose |
|---|---|
| `GET /` | API info |
| `GET /products` | List products |
| `GET /cart` | Demo cart summary |
| `POST /cart/items` | Demo cart add item |
| `DELETE /cart/items/<product_id>` | Demo cart remove item |
| `POST /checkout` | Demo checkout |
| `GET /orders` | List demo orders |
| `GET /metrics` | Prometheus metrics |
| `GET /healthz` | Health check |

Custom metrics:

| Metric | Purpose |
|---|---|
| `orders_api_http_requests_total` | Request count by method, endpoint, status |
| `orders_api_request_latency_seconds` | Request latency histogram |
| `shopping_cart_items` | Current cart item count |
| `shopping_cart_value_usd` | Current cart value |
| `shopping_cart_checkouts_total` | Successful checkout count |

### user-api

Folder:

```text
services/user-api/
```

Purpose:

- Provides user data
- Connects to MySQL
- Creates a users table if possible
- Falls back to in-memory users if MySQL is unavailable

Important routes:

| Route | Purpose |
|---|---|
| `GET /` | API info |
| `GET /users` | List users |
| `GET /users/<user_id>` | Get one user |
| `GET /metrics` | Prometheus metrics |
| `GET /healthz` | Health check |

### cart-api

Folder:

```text
services/cart-api/
```

Purpose:

- Stores shopping cart by user
- Uses Redis as primary storage
- Falls back to in-memory cart if Redis is unavailable

Important routes:

| Route | Purpose |
|---|---|
| `GET /` | API info |
| `GET /cart/<user_id>` | Get user cart |
| `POST /cart/items` | Add item |
| `DELETE /cart/items/<product_id>` | Remove item |
| `POST /cart/clear` | Clear cart |
| `GET /metrics` | Prometheus metrics |
| `GET /healthz` | Health check |

### payment-api

Folder:

```text
services/payment-api/
```

Purpose:

- Simulates payment authorization
- Creates payment IDs
- Randomly declines a small percentage of requests to generate realistic failure logs

Important route:

```text
POST /payments
```

### shipping-api

Folder:

```text
services/shipping-api/
```

Purpose:

- Simulates shipment creation
- Creates shipment IDs
- Returns carrier and label status

Important route:

```text
POST /shipments
```

## 13. Python Implementation Details

All application services use Python Flask.

Shared dependency file:

```text
services/common/requirements.txt
```

Important Python packages:

| Package | Why it is used |
|---|---|
| `flask` | Build HTTP APIs and frontend |
| `requests` | Frontend calls backend APIs |
| `opentelemetry-*` | Export distributed traces |
| `prometheus-client` | Expose metrics at `/metrics` |
| `redis` | Cart API connects to Redis |
| `pymysql` | User API connects to MySQL |

### Shared Observability Code

File:

```text
services/common/observability.py
```

This helper does the common setup for services:

- Configures Python logging
- Configures OpenTelemetry tracer provider
- Exports traces to `otel-collector:4317`
- Instruments Flask automatically
- Creates Prometheus request counter
- Creates Prometheus request latency histogram
- Adds `/metrics`
- Adds `/healthz`
- Adds simulated latency for realistic metrics

This avoids repeating the same observability code in every service.

### Why Flask Was Used

Flask is simple and good for learning microservices:

- Easy to define HTTP routes
- Easy to expose JSON APIs
- Easy to add Prometheus metrics
- Easy to add OpenTelemetry instrumentation
- Easy to containerize with Docker

### How Logs Are Produced

Each service writes logs to stdout using Python logging.

Example log style:

```text
service=cart-api message=cart item added user_id=u100 product_id=p100 total=49.99
```

Kubernetes stores container stdout logs on the node. Promtail and Fluent Bit read those logs and send them to Loki and Elasticsearch.

## 14. Docker Implementation

Each Python service is packaged as a Docker image.

Common Docker pattern:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
EXPOSE 8080
CMD ["python", "app.py"]
```

For services under `services/`, Dockerfiles copy:

- Shared requirements
- Shared observability helper
- Service `app.py`
- Frontend templates and static CSS when needed

### Local Build Commands

```powershell
docker build -t orders-api:local .\app
docker build -t shopping-frontend:local -f .\services\frontend\Dockerfile .
docker build -t user-api:local -f .\services\user-api\Dockerfile .
docker build -t cart-api:local -f .\services\cart-api\Dockerfile .
docker build -t payment-api:local -f .\services\payment-api\Dockerfile .
docker build -t shipping-api:local -f .\services\shipping-api\Dockerfile .
```

### Why Kind Needs Image Loading

Kind runs Kubernetes nodes as Docker containers. The Kubernetes node has its own container runtime.

So after building images locally, load them into the Kind cluster:

```powershell
kind load docker-image orders-api:local --name observability
kind load docker-image shopping-frontend:local --name observability
kind load docker-image user-api:local --name observability
kind load docker-image cart-api:local --name observability
kind load docker-image payment-api:local --name observability
kind load docker-image shipping-api:local --name observability
```

Or use:

```powershell
.\scripts\build-load-kind.ps1
```

### Interview Explanation For Docker

```text
Each microservice has its own Docker image. I used python:3.12-slim as the base
image, installed dependencies, copied service code, exposed port 8080, and started
the service with python app.py. Since this is a local Kind cluster, I built images
locally and loaded them into Kind using kind load docker-image.
```

## 15. Kubernetes Implementation Details

Each service generally has:

- Deployment
- Service
- Labels
- Environment variables
- Resource requests and limits
- Readiness probe
- Liveness probe

Example pattern:

```yaml
readinessProbe:
  httpGet:
    path: /healthz
    port: 8080
livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
```

### Why Readiness And Liveness Probes Matter

| Probe | Meaning |
|---|---|
| Readiness | Should this pod receive traffic? |
| Liveness | Is this pod healthy or should Kubernetes restart it? |

If readiness fails, the pod may run but the service will not send traffic to it.

### Why Services Are Needed

Pods are temporary. Their IPs can change.

Kubernetes Services give stable DNS names:

```text
frontend
orders-api
cart-api
user-api
payment-api
shipping-api
mysql
redis
```

The frontend can call:

```text
http://cart-api:8080
```

without knowing the cart pod IP.

## 16. Observability Overview

The project demonstrates the three pillars of observability:

| Signal | Tooling |
|---|---|
| Metrics | Prometheus and Grafana |
| Logs | Loki, Promtail, Elasticsearch, Fluent Bit, Kibana |
| Traces | OpenTelemetry Collector and Jaeger |

### Metrics Flow

```text
Python Flask services
  expose /metrics
  |
  v
Prometheus
  scrapes metrics
  |
  v
Grafana
  displays dashboards
```

Prometheus config:

```text
k8s/50-prometheus.yaml
```

Grafana config:

```text
k8s/70-grafana.yaml
```

Useful PromQL:

```promql
sum(rate(orders_api_http_requests_total[1m])) by (endpoint)
```

```promql
histogram_quantile(0.95, sum(rate(orders_api_request_latency_seconds_bucket[5m])) by (le, endpoint))
```

```promql
shopping_cart_items
```

### Logs Flow With Loki

```text
Pod stdout logs
  |
  v
Promtail
  |
  v
Loki
  |
  v
Grafana Explore
```

Config:

```text
k8s/60-loki-promtail.yaml
```

Useful LogQL:

```logql
{app="frontend"}
```

```logql
{app="orders-api"} |= "cart"
```

```logql
{app="cart-api"} |= "cart item added"
```

### Logs Flow With Elasticsearch And Kibana

```text
Pod stdout logs
  |
  v
Fluent Bit
  |
  v
Elasticsearch
  |
  v
Kibana Discover
```

Config:

```text
k8s/30-efk.yaml
```

Kibana login:

```text
URL: http://kibana.observability.local
username: elastic
password: ElasticDemo123!
```

Kibana data view:

```text
k8s-logs*
```

Time field:

```text
@timestamp
```

### Traces Flow

```text
Python Flask services
  |
  | OTLP traces
  v
OpenTelemetry Collector
  |
  v
Jaeger
```

Config:

```text
k8s/20-otel-collector.yaml
k8s/10-jaeger.yaml
```

Jaeger URL:

```text
http://jaeger.observability.local
```

Search services such as:

```text
frontend
cart-api
payment-api
shipping-api
orders-api
```

## 17. Important URLs And Logins

### Application URLs

| URL | Purpose |
|---|---|
| `http://shop.observability.local` | Main shopping web app |
| `http://orders.observability.local/products` | Products API |
| `http://orders.observability.local/orders` | Orders API |
| `http://cart.observability.local` | Cart API |
| `http://users.observability.local/users` | Users API |
| `http://payment.observability.local` | Payment API |
| `http://shipping.observability.local` | Shipping API |

### Observability URLs

| URL | Tool |
|---|---|
| `http://grafana.observability.local` | Grafana |
| `http://prometheus.observability.local` | Prometheus |
| `http://jaeger.observability.local` | Jaeger |
| `http://kibana.observability.local` | Kibana |
| `http://loki.observability.local/loki/api/v1/label/app/values` | Loki labels API |

### Logins

| Tool | Username | Password |
|---|---|---|
| Grafana | `admin` | `admin` |
| Kibana | `elastic` | `ElasticDemo123!` |
| Argo CD | `admin` | Initial password from Kubernetes secret |

## 18. End-To-End Request Flow

When a user opens:

```text
http://shop.observability.local
```

Flow:

```text
Browser
  -> NGINX Ingress
  -> frontend service
  -> frontend pod
  -> backend services
```

When the page loads:

```text
frontend -> orders-api -> products
frontend -> user-api -> user profile
frontend -> cart-api -> cart state
```

When a user adds an item:

```text
frontend -> cart-api -> Redis
```

When a user checks out:

```text
frontend
  -> cart-api
  -> payment-api
  -> shipping-api
  -> cart-api clear
```

At the same time:

```text
metrics -> Prometheus -> Grafana
logs -> Promtail -> Loki -> Grafana
logs -> Fluent Bit -> Elasticsearch -> Kibana
traces -> OpenTelemetry Collector -> Jaeger
```

## 19. Generate Demo Traffic

Open the web app and click:

- Add
- Checkout
- Clear cart

Or run:

```powershell
curl.exe http://shop.observability.local/checkout-demo
curl.exe http://orders.observability.local/products
curl.exe http://users.observability.local/users
```

PowerShell POST example:

```powershell
$body = @{ user_id = "u100"; product_id = "p100"; quantity = 1 } | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://cart.observability.local/cart/items" `
  -ContentType "application/json" `
  -Body $body
```

## 20. Health Check Commands

Check context:

```powershell
kubectl config current-context
```

Check pods:

```powershell
kubectl get pods -n observability-demo
```

Check deployments:

```powershell
kubectl get deploy -n observability-demo
```

Wait for all deployments:

```powershell
kubectl wait --for=condition=available deployment --all -n observability-demo --timeout=300s
```

Run the project health script:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check-deployment.ps1 -TimeoutSeconds 300
```

Run the health script with ingress checks:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check-deployment.ps1 -TimeoutSeconds 300 -TestIngress -IngressUrl http://localhost
```

## 21. Troubleshooting Guide

### Problem: Kind Cluster Already Exists

Symptom:

```text
node(s) already exist for a cluster with the name "observability"
```

Meaning:

The Kind cluster already exists.

Fix:

```powershell
kubectl config use-context kind-observability
```

If you want to recreate from zero:

```powershell
kind delete cluster --name observability
kind create cluster --config .\kind-config.yaml
```

### Problem: Ingress Controller Timeout

Symptom:

```text
timed out waiting for the condition on pods/ingress-nginx-controller
```

Check:

```powershell
kubectl get pods -n ingress-nginx -o wide
kubectl describe pod -n ingress-nginx -l app.kubernetes.io/component=controller
```

Common fix:

Make sure the Kind node has this label:

```powershell
kubectl label node observability-control-plane ingress-ready=true --overwrite
```

Then wait again:

```powershell
kubectl wait --namespace ingress-nginx --for=condition=ready pod --selector=app.kubernetes.io/component=controller --timeout=180s
```

### Problem: Port 8080 Already In Use

Symptom:

```text
Unable to listen on port 8080
Only one usage of each socket address is normally permitted
```

Meaning:

Something is already using local port `8080`.

Fix option 1, use ingress instead:

```text
http://shop.observability.local
```

Fix option 2, use a different local port:

```powershell
kubectl port-forward svc/frontend 8082:8080 -n observability-demo
```

Open:

```text
http://localhost:8082
```

### Problem: Hostname Cannot Resolve

Symptom:

```text
Could not resolve host: shop.observability.local
```

Fix:

Add entries from:

```text
scripts/hosts-entries.txt
```

to:

```text
C:\Windows\System32\drivers\etc\hosts
```

Then:

```powershell
ipconfig /flushdns
```

### Problem: PowerShell curl Errors

Symptom:

```text
Cannot bind parameter 'Headers'
A parameter cannot be found that matches parameter name 'X'
```

Meaning:

In PowerShell, `curl` is an alias for `Invoke-WebRequest`, not real curl.

Fix:

Use:

```powershell
curl.exe http://shop.observability.local
```

For headers:

```powershell
curl.exe -H "Host: shop.observability.local" http://localhost
```

Or use PowerShell syntax:

```powershell
Invoke-RestMethod -Uri "http://shop.observability.local"
```

### Problem: ImagePullBackOff

Symptom:

```text
ImagePullBackOff
ErrImagePull
```

Meaning:

Kubernetes cannot find or pull the image.

For Kind, local images must be loaded.

Fix:

```powershell
.\scripts\build-load-kind.ps1
kubectl rollout restart deployment/frontend -n observability-demo
kubectl rollout restart deployment/orders-api -n observability-demo
kubectl rollout restart deployment/cart-api -n observability-demo
```

Check images inside Kind:

```powershell
docker exec -it observability-control-plane crictl images
```

### Problem: Pod Running But Not Ready

Symptom:

```text
0/1 Running
```

Check:

```powershell
kubectl describe pod <pod-name> -n observability-demo
kubectl logs <pod-name> -n observability-demo
```

Common causes:

- `/healthz` endpoint failing
- App crashed during startup
- Wrong environment variable
- Backend dependency unavailable

### Problem: Service Returns 503

Symptom:

```text
503 Service Temporarily Unavailable
```

Check endpoints:

```powershell
kubectl get endpoints -n observability-demo
kubectl get pods -n observability-demo --show-labels
kubectl describe svc frontend -n observability-demo
```

Meaning:

The Service may not match any pods.

Fix example:

```powershell
kubectl patch svc orders-api -n observability-demo --type merge -p '{\"spec\":{\"selector\":{\"app\":\"orders-api\"}}}'
```

### Problem: Prometheus Target Down

Open:

```text
http://prometheus.observability.local/targets
```

Check:

```powershell
kubectl logs deploy/prometheus -n observability-demo
kubectl get configmap prometheus-config -n observability-demo -o yaml
curl.exe http://orders.observability.local/metrics
```

Common cause:

- Wrong metrics path
- Service DNS wrong
- App `/metrics` endpoint not working

Fix:

```powershell
kubectl apply -k .\k8s
kubectl rollout restart deployment/prometheus -n observability-demo
```

### Problem: Grafana Loki Query Parse Error

Symptom:

```text
bad_data: invalid parameter "query": parse error: unexpected character: '|'
```

Correct LogQL:

```logql
{app="orders-api"} |= "cart"
```

Incorrect:

```logql
{app="orders-api"} | = "cart"
```

Also confirm the selected data source is `Loki`, not Prometheus.

### Problem: Loki Shows No Logs

Check Promtail:

```powershell
kubectl logs ds/promtail -n observability-demo --tail=100
```

Check Loki labels:

```powershell
curl.exe http://loki.observability.local/loki/api/v1/label/app/values
```

Generate traffic:

```powershell
curl.exe http://shop.observability.local/checkout-demo
```

Then query in Grafana Explore:

```logql
{app="frontend"}
{app="cart-api"}
{app="payment-api"}
```

### Problem: Kibana Asks To Enable Security

Meaning:

Some Kibana features need Elasticsearch security enabled.

This project enables security in:

```text
k8s/30-efk.yaml
```

Browser login:

```text
elastic / ElasticDemo123!
```

Check Elasticsearch auth:

```powershell
kubectl exec -n observability-demo deploy/elasticsearch -- curl -s -u "elastic:ElasticDemo123!" http://localhost:9200/_cluster/health?pretty
```

### Problem: Kibana Discover Shows No Logs

Check if Elasticsearch has documents:

```powershell
kubectl exec -n observability-demo deploy/elasticsearch -- curl -s -u "elastic:ElasticDemo123!" http://localhost:9200/k8s-logs/_count?pretty
```

If count is greater than zero, create or select data view:

```text
k8s-logs*
```

Time field:

```text
@timestamp
```

### Problem: Jaeger Shows No Traces

Generate traffic:

```powershell
curl.exe http://shop.observability.local/checkout-demo
```

Check OpenTelemetry Collector:

```powershell
kubectl logs deploy/otel-collector -n observability-demo --tail=100
```

Check app env var:

```powershell
kubectl get deploy frontend -n observability-demo -o jsonpath="{.spec.template.spec.containers[0].env}"
```

Expected:

```text
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
```

Fix example:

```powershell
kubectl set env deployment/frontend OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317 -n observability-demo
```

### Problem: Argo CD Shows OutOfSync

Meaning:

Live cluster state is different from Git.

Check:

```powershell
kubectl get application observability-stack -n argocd -o yaml
```

Fix:

Sync from Argo CD UI or run:

```powershell
argocd app sync observability-stack
```

If using kubectl only:

```powershell
kubectl annotate application observability-stack -n argocd argocd.argoproj.io/refresh=hard --overwrite
```

### Problem: Argo CD Healthy But App Image Still Old

Meaning:

Argo CD applied the YAML, but the YAML still references the old image.

Check:

```powershell
kubectl get deployment orders-api -n observability-demo -o jsonpath="{.spec.template.spec.containers[0].image}"
```

Fix:

- Update image in Git
- Commit and push
- Let Argo CD sync

For Kind, also build and load the new image:

```powershell
docker build -t orders-api:v2 .\app
kind load docker-image orders-api:v2 --name observability
```

### Problem: MySQL Or Redis Not Ready

Check:

```powershell
kubectl get pods -n observability-demo -l app=mysql
kubectl get pods -n observability-demo -l app=redis
kubectl logs deploy/mysql -n observability-demo
kubectl logs deploy/redis -n observability-demo
```

Common causes:

- Container still starting
- Not enough memory
- Probe delay too short

In this demo, the Python services have fallback behavior so the app can still respond even if MySQL or Redis is temporarily unavailable.

### Problem: Checkout Fails

Common causes:

- Cart is empty
- payment-api randomly declined payment
- payment-api or shipping-api not ready

Check:

```powershell
kubectl logs deploy/frontend -n observability-demo --tail=100
kubectl logs deploy/payment-api -n observability-demo --tail=100
kubectl logs deploy/shipping-api -n observability-demo --tail=100
```

Generate a known demo checkout:

```powershell
curl.exe http://shop.observability.local/checkout-demo
```

## 22. Troubleshooting Order For Any Issue

Use this order in interviews and real debugging:

```powershell
kubectl config current-context
kubectl get ns
kubectl get pods -n observability-demo
kubectl get deploy -n observability-demo
kubectl get svc -n observability-demo
kubectl get ingress -n observability-demo
kubectl get endpoints -n observability-demo
kubectl describe pod <pod-name> -n observability-demo
kubectl logs <pod-name> -n observability-demo
kubectl get events -n observability-demo --sort-by=.lastTimestamp
```

Then check the specific layer:

| Layer | What to check |
|---|---|
| Browser | URL, hosts file, DNS |
| Ingress | Ingress rules, ingress controller |
| Service | Selector and endpoints |
| Pod | Status, readiness, logs |
| Image | Image name, image loaded into Kind |
| App | `/healthz`, `/metrics`, logs |
| Observability | Prometheus targets, Loki labels, Jaeger services, Kibana data view |
| GitOps | Argo CD sync, health, repo path |

## 23. Argo CD Upgrade And Rollback

Upgrade overlay:

```text
k8s-upgrades/v2
```

Argo CD app for v2:

```text
argocd/applications/observability-app-v2.yaml
```

The v2 overlay changes:

- `orders-api:local` to `orders-api:v2`
- `APP_VERSION=v1` to `APP_VERSION=v2`
- pod label `version=v2`

Build and load the v2 image:

```powershell
docker build -t orders-api:v2 .\app
kind load docker-image orders-api:v2 --name observability
```

Apply v2 Argo CD app:

```powershell
kubectl apply -f .\argocd\applications\observability-app-v2.yaml
```

Rollback:

```powershell
kubectl apply -f .\argocd\applications\observability-app.yaml
```

Interview explanation:

```text
For upgrades, I created a Kustomize overlay that changes the image tag and
application version. Argo CD points to the overlay and syncs the new desired state.
For rollback, I point Argo CD back to the original base application.
```

## 24. What Makes This Enterprise-Like

This is a local learning project, but it demonstrates enterprise patterns:

| Enterprise Pattern | How This Project Shows It |
|---|---|
| GitOps | Argo CD deploys from Git |
| Microservices | Separate frontend and backend services |
| Containerization | Each service has a Docker image |
| Kubernetes | Deployments, Services, Ingress, ConfigMaps, Secrets |
| Health checks | Readiness and liveness probes |
| Metrics | Prometheus scraping `/metrics` |
| Logs | Loki and Elasticsearch pipelines |
| Traces | OpenTelemetry and Jaeger |
| Dashboards | Grafana provisioning |
| Security scanning | Trivy, Checkov, Gitleaks, Hadolint, Bandit |
| Troubleshooting labs | Broken overlays for practice |

## 25. What Would Be Improved For Real Production

For a real enterprise system, improve these areas:

| Current Local Demo | Production Improvement |
|---|---|
| Local Kind cluster | Managed Kubernetes like EKS, AKS, or GKE |
| Local image tags | Registry images with immutable tags |
| Plain Kubernetes secrets | External Secrets with Vault or cloud secret manager |
| Single-node Elasticsearch | Managed Elasticsearch or multi-node cluster |
| Simple Grafana admin password | SSO and RBAC |
| No TLS for app hostnames | HTTPS certificates with cert-manager |
| In-memory fallbacks | Strong persistent data design |
| Static Prometheus config | ServiceMonitor with Prometheus Operator |
| Basic Argo CD app | AppProjects, RBAC, sync waves, app-of-apps |
| Demo resource limits | Capacity planning and autoscaling |

## 26. Best Interview Talking Points

### Why Argo CD?

```text
Argo CD gives GitOps deployment. It continuously compares the desired state in Git
with the live Kubernetes cluster. This makes deployments auditable, repeatable,
and easier to roll back.
```

### Why Kustomize?

```text
Kustomize lets me organize Kubernetes YAML into a base and overlays without using
templates. I used the k8s folder as the base and k8s-upgrades/v2 as an upgrade
overlay.
```

### Why OpenTelemetry?

```text
OpenTelemetry gives a vendor-neutral way to instrument applications and export
traces. My Python services export OTLP traces to the OpenTelemetry Collector,
which forwards them to Jaeger.
```

### Why Prometheus?

```text
Prometheus is used for metrics because applications can expose /metrics and
Prometheus can scrape them on an interval. I used counters and histograms to
track request rate and latency.
```

### Why Loki And Elasticsearch Both?

```text
I used Loki with Grafana to practice lightweight log querying with LogQL, and
Elasticsearch with Kibana to practice EFK-style log search. This lets me compare
two common logging approaches.
```

### Why Readiness And Liveness Probes?

```text
Readiness controls whether a pod receives traffic. Liveness controls whether
Kubernetes should restart a stuck container. They are important for reliable
rollouts and self-healing.
```

### How Do You Debug A 503?

```text
I start from ingress, then service, then endpoints, then pods. A 503 often means
the service has no ready endpoints, usually because labels do not match, pods are
not ready, or readiness probes are failing.
```

### How Do You Debug Missing Logs?

```text
First I confirm the application is producing logs with kubectl logs. Then I check
the log collector, such as Promtail or Fluent Bit. Then I check whether Loki labels
or Elasticsearch indices contain data. Finally I verify the Grafana or Kibana query.
```

### How Do You Debug Missing Traces?

```text
I generate traffic, check the application OTEL endpoint environment variable, check
OpenTelemetry Collector logs, and then check Jaeger for the service name.
```

## 27. Short Interview Summary

Use this when you need a compact answer:

```text
This is a Kubernetes GitOps and observability project. I built a Python Flask
shopping platform with frontend, user, cart, orders, payment, and shipping services.
Each service is containerized with Docker and deployed to a Kind Kubernetes cluster.

The manifests are organized with Kustomize and deployed through Argo CD. Argo CD
watches the Git repo, syncs the k8s folder, prunes removed resources, and self-heals
manual drift.

For observability, services expose Prometheus metrics, write logs to stdout, and
export traces with OpenTelemetry. Prometheus and Grafana handle metrics, Promtail
and Loki handle Grafana logs, Fluent Bit and Elasticsearch handle Kibana logs, and
OpenTelemetry Collector sends traces to Jaeger.

I also added troubleshooting labs for ImagePullBackOff, service selector mismatch,
readiness failures, missing traces, Prometheus target down, Loki logs missing,
Kibana issues, and YAML syntax errors.
```

## 28. Files To Remember

| File or Folder | Why It Matters |
|---|---|
| `argocd/applications/observability-app.yaml` | Main Argo CD GitOps app |
| `k8s/kustomization.yaml` | Lists all Kubernetes modules |
| `k8s/80-ingress.yaml` | Browser routing |
| `k8s/50-prometheus.yaml` | Metrics collection |
| `k8s/60-loki-promtail.yaml` | Loki log pipeline |
| `k8s/30-efk.yaml` | Elasticsearch, Fluent Bit, Kibana |
| `k8s/20-otel-collector.yaml` | Trace collection |
| `k8s/10-jaeger.yaml` | Trace UI |
| `k8s/70-grafana.yaml` | Dashboards and data sources |
| `services/common/observability.py` | Shared Python observability setup |
| `services/frontend/app.py` | Frontend web app |
| `services/frontend/templates/index.html` | Frontend HTML |
| `services/frontend/static/styles.css` | Frontend CSS |
| `app/app.py` | orders-api |
| `services/cart-api/app.py` | cart-api |
| `services/user-api/app.py` | user-api |
| `services/payment-api/app.py` | payment-api |
| `services/shipping-api/app.py` | shipping-api |
| `scripts/build-load-kind.ps1` | Build and load Docker images into Kind |
| `scripts/check-deployment.ps1` | Health check script |
| `troubleshooting-labs/` | Practice broken Kubernetes scenarios |

## 29. Final Beginner Mental Model

Remember the project like this:

```text
Argo CD deploys from Git.
Kustomize organizes Kubernetes YAML.
Docker packages Python services.
Kind runs Kubernetes locally.
Ingress exposes friendly URLs.
Frontend calls backend APIs.
Redis stores carts.
MySQL stores users.
Prometheus stores metrics.
Grafana shows dashboards.
Loki stores logs for Grafana.
Elasticsearch stores logs for Kibana.
OpenTelemetry collects traces.
Jaeger shows traces.
Troubleshooting starts from context, pods, services, endpoints, logs, and events.
```

That is the complete story of this project.
