# Shopping App Observability Walkthrough

This document explains the local Kubernetes shopping application in simple terms. Use it when you want to remember what each piece does, how to open the app, and how Grafana, Prometheus, Loki, Jaeger, Kibana, and Elasticsearch fit together.

## 1. What This Project Runs

This project runs a small shopping platform on a local Kind Kubernetes cluster.

The application has these main services:

| Service | Purpose |
|---|---|
| `frontend` | Web page for the shopping app |
| `orders-api` | Product list, orders, cart metrics |
| `cart-api` | Cart storage using Redis |
| `user-api` | User data using MySQL |
| `payment-api` | Demo payment authorization |
| `shipping-api` | Demo shipment creation |
| `redis` | Stores cart data |
| `mysql` | Stores user-style relational data |

The frontend is now a real web page with:

- Logo and header
- Product cards
- Cart panel
- Add to cart
- Remove item
- Clear cart
- Checkout
- Service status
- Links to observability tools
- Links to backend API routes

Open the app here:

```text
http://shop.observability.local
```

## 2. Local Hostnames

The app uses local DNS names like:

```text
shop.observability.local
grafana.observability.local
jaeger.observability.local
```

These are not real internet domains. They point to your local machine using the Windows hosts file.

The hosts file entries should look like this:

```text
127.0.0.1 shop.observability.local
127.0.0.1 orders.observability.local
127.0.0.1 cart.observability.local
127.0.0.1 users.observability.local
127.0.0.1 payment.observability.local
127.0.0.1 shipping.observability.local
127.0.0.1 grafana.observability.local
127.0.0.1 prometheus.observability.local
127.0.0.1 jaeger.observability.local
127.0.0.1 kibana.observability.local
127.0.0.1 loki.observability.local
```

If these are missing, add them from PowerShell opened as Administrator:

```powershell
$hostsPath = "$env:SystemRoot\System32\drivers\etc\hosts"

$entries = @"
127.0.0.1 shop.observability.local
127.0.0.1 orders.observability.local
127.0.0.1 cart.observability.local
127.0.0.1 users.observability.local
127.0.0.1 payment.observability.local
127.0.0.1 shipping.observability.local
127.0.0.1 grafana.observability.local
127.0.0.1 prometheus.observability.local
127.0.0.1 jaeger.observability.local
127.0.0.1 kibana.observability.local
127.0.0.1 loki.observability.local
"@

Add-Content -Path $hostsPath -Value "`n# k8s observability local hosts`n$entries"
ipconfig /flushdns
```

## 3. Important URLs

### Application URLs

| URL | What it opens |
|---|---|
| `http://shop.observability.local` | Main shopping web app |
| `http://orders.observability.local/products` | Products API |
| `http://orders.observability.local/orders` | Orders API |
| `http://cart.observability.local` | Cart API info |
| `http://users.observability.local/users` | Users API |
| `http://payment.observability.local` | Payment API info |
| `http://shipping.observability.local` | Shipping API info |

### Observability URLs

| URL | Tool | Use |
|---|---|---|
| `http://grafana.observability.local` | Grafana | Dashboards for metrics and logs |
| `http://prometheus.observability.local` | Prometheus | Raw metrics and PromQL |
| `http://jaeger.observability.local` | Jaeger | Distributed traces |
| `http://kibana.observability.local` | Kibana | Elasticsearch log search |
| `http://loki.observability.local/loki/api/v1/label/app/values` | Loki API | Check log labels |

## 4. How Traffic Flows

The request flow looks like this:

```text
Browser
  -> NGINX Ingress
  -> frontend
  -> backend services
       -> orders-api
       -> cart-api
       -> user-api
       -> payment-api
       -> shipping-api
```

Example:

When you open:

```text
http://shop.observability.local
```

The request goes to the frontend. The frontend then calls other services to load products, user data, cart data, and service health.

When you click checkout, the frontend calls:

```text
cart-api
payment-api
shipping-api
```

This creates useful metrics, logs, and traces.

## 5. How Observability Works

This project uses three major observability signals.

### Metrics

Metrics show numbers over time.

Examples:

- HTTP request count
- Request latency
- Cart item count
- Cart value

Metrics flow:

```text
Application metrics
  -> Prometheus
  -> Grafana dashboard
```

Use Grafana or Prometheus to view metrics.

### Logs

Logs show what happened inside services.

Examples:

```text
cart item added
checkout completed
payment authorized
shipment created
```

Loki log flow:

```text
Pod log files
  -> Promtail
  -> Loki
  -> Grafana Explore
```

Elasticsearch log flow:

```text
Pod log files
  -> Fluent Bit
  -> Elasticsearch
  -> Kibana
```

### Traces

Traces show how one request moves across services.

Example:

```text
frontend checkout
  -> cart-api
  -> payment-api
  -> shipping-api
```

Trace flow:

```text
Application spans
  -> OpenTelemetry Collector
  -> Jaeger
```

Use Jaeger to debug where a request spent time.

## 6. Useful Commands

Check all pods:

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

View frontend logs:

```powershell
kubectl logs deploy/frontend -n observability-demo --tail=100
```

View cart logs:

```powershell
kubectl logs deploy/cart-api -n observability-demo --tail=100
```

View Promtail logs:

```powershell
kubectl logs ds/promtail -n observability-demo --tail=100
```

View Loki labels:

```powershell
curl.exe http://loki.observability.local/loki/api/v1/label/app/values
```

## 7. Generate Demo Traffic

Open the web app and click buttons:

```text
http://shop.observability.local
```

Or use PowerShell:

```powershell
curl.exe http://orders.observability.local/products
curl.exe http://shop.observability.local/checkout-demo
```

For a POST request from PowerShell:

```powershell
$body = @{ product_id = "p100"; quantity = 1 } | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://orders.observability.local/cart/items" `
  -ContentType "application/json" `
  -Body $body
```

Then refresh Grafana, Loki, Kibana, or Jaeger.

## 8. Grafana Beginner Queries

Open Grafana:

```text
http://grafana.observability.local
```

Login:

```text
admin / admin
```

### Prometheus Queries

Request rate:

```promql
sum(rate(orders_api_http_requests_total[1m])) by (endpoint)
```

P95 latency:

```promql
histogram_quantile(
  0.95,
  sum(rate(orders_api_request_latency_seconds_bucket[5m])) by (le, endpoint)
)
```

Cart items:

```promql
shopping_cart_items
```

Cart value:

```promql
shopping_cart_value_usd
```

### Loki Queries

Choose data source:

```text
Loki
```

Show orders-api logs:

```logql
{app="orders-api"}
```

Show cart-related orders-api logs:

```logql
{app="orders-api"} |= "cart"
```

Show frontend logs:

```logql
{app="frontend"}
```

Show checkout logs:

```logql
{app="frontend"} |= "checkout"
```

If you get a parse error, confirm you selected the Loki data source, not Prometheus.

## 9. Rebuild After Frontend Changes

If you change frontend HTML, CSS, or Python code, rebuild and reload the image:

```powershell
docker build -t shopping-frontend:local -f .\services\frontend\Dockerfile .
kind load docker-image shopping-frontend:local --name observability
kubectl rollout restart deployment/frontend -n observability-demo
kubectl rollout status deployment/frontend -n observability-demo --timeout=180s
```

Then open:

```text
http://shop.observability.local
```

## 10. Rebuild After Cart API Changes

If you change the cart API:

```powershell
docker build -t cart-api:local -f .\services\cart-api\Dockerfile .
kind load docker-image cart-api:local --name observability
kubectl rollout restart deployment/cart-api -n observability-demo
kubectl rollout status deployment/cart-api -n observability-demo --timeout=180s
```

## 11. Common Problems

### Hostname Not Found

Error:

```text
Could not resolve host: shop.observability.local
```

Fix:

Add the host entries to:

```text
C:\Windows\System32\drivers\etc\hosts
```

Then run:

```powershell
ipconfig /flushdns
```

### PowerShell Curl Error

In PowerShell, `curl` is an alias for `Invoke-WebRequest`.

Use:

```powershell
curl.exe http://shop.observability.local
```

Or PowerShell-native syntax:

```powershell
Invoke-RestMethod http://shop.observability.local
```

### Loki Shows No Logs

Check Promtail:

```powershell
kubectl logs ds/promtail -n observability-demo --tail=100
```

Check Loki labels:

```powershell
curl.exe http://loki.observability.local/loki/api/v1/label/app/values
```

Expected labels include:

```text
frontend
orders-api
cart-api
payment-api
shipping-api
```

### Grafana Query Parse Error

If this fails:

```logql
{app="orders-api"} |= "cart"
```

Check:

- Data source is `Loki`
- Query is in Code mode
- There is no space between `|` and `=`

Correct:

```logql
{app="orders-api"} |= "cart"
```

Incorrect:

```logql
{app="orders-api"} | = "cart"
```

## 12. Simple Mental Model

Remember it like this:

```text
Kind runs Kubernetes locally.
Ingress gives friendly URLs.
Frontend is the web app.
Backend APIs do shopping work.
Prometheus stores metrics.
Grafana shows dashboards.
Loki stores logs for Grafana.
Elasticsearch stores logs for Kibana.
Jaeger shows traces.
```

That is the full local observability platform.
