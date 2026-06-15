# Kubernetes Observability Project with Kind, OpenTelemetry, EFK, Loki, Prometheus, Grafana, and Jaeger

This project runs a small `orders-api` application on a Kind Kubernetes cluster and connects it to:

- OpenTelemetry Collector for trace collection
- Jaeger for distributed tracing
- EFK stack: Elasticsearch, Fluent Bit, and Kibana for logs
- Prometheus for metrics and PromQL
- Loki + Promtail for log aggregation and LogQL
- Grafana for Prometheus metrics, Loki logs, and Jaeger traces
- Optional Argo CD GitOps deployment and error-recovery labs

## Architecture

```text
curl/browser
   |
   v
orders-api service
   |
   v
orders-api pods
   |                         |                       |
   | OTLP traces             | /metrics              | stdout logs
   v                         v                       v
OpenTelemetry Collector      Prometheus              Fluent Bit -> Elasticsearch -> Kibana
   |                         |                       |
   v                         v                       v
Jaeger                       Grafana                 Promtail -> Loki -> Grafana
```

## Prerequisites

Install these tools:

- Docker
- Kind
- kubectl

Check them:

```bash
docker --version
kind --version
kubectl version --client
```

## Step 1: Create a Kind Cluster

Create a cluster named `observability`:

```bash
kind create cluster --name observability
```

Confirm the cluster is running:

```bash
kubectl cluster-info --context kind-observability
kubectl get nodes
```

If you already have a Kind cluster, make sure `kubectl` points to it:

```bash
kubectl config use-context kind-observability
```

## Step 2: Build the Application Docker Image

From this project folder:

```bash
docker build -t orders-api:local ./app
```

## Step 3: Load the Image into Kind

Kind does not automatically see images from your local Docker engine. Load the image into the Kind cluster:

```bash
kind load docker-image orders-api:local --name observability
```

Verify the image is available inside the Kind node:

```bash
docker exec -it observability-control-plane crictl images | grep orders-api
```

On Windows PowerShell, use:

```powershell
docker exec -it observability-control-plane crictl images | Select-String orders-api
```

## Step 4: Deploy the Project

Deploy the namespace, app, OpenTelemetry Collector, Jaeger, Elasticsearch, Fluent Bit, Kibana, Prometheus, Loki, Promtail, and Grafana:

```bash
kubectl apply -k ./k8s
```

Check all pods:

```bash
kubectl get pods -n observability-demo
```

Wait for the main deployments:

```bash
kubectl wait --for=condition=available deployment/orders-api -n observability-demo --timeout=180s
kubectl wait --for=condition=available deployment/otel-collector -n observability-demo --timeout=180s
kubectl wait --for=condition=available deployment/jaeger -n observability-demo --timeout=180s
kubectl wait --for=condition=available deployment/elasticsearch -n observability-demo --timeout=300s
kubectl wait --for=condition=available deployment/kibana -n observability-demo --timeout=300s
kubectl wait --for=condition=available deployment/prometheus -n observability-demo --timeout=180s
kubectl wait --for=condition=available deployment/loki -n observability-demo --timeout=180s
kubectl wait --for=condition=available deployment/grafana -n observability-demo --timeout=180s
```

Check Fluent Bit and Promtail:

```bash
kubectl get daemonset fluent-bit -n observability-demo
kubectl get daemonset promtail -n observability-demo
```

## Step 5: Test the Application

Port-forward the app service:

```bash
kubectl port-forward svc/orders-api 8080:8080 -n observability-demo
```

Open another terminal and send traffic:

```bash
curl http://localhost:8080/
curl http://localhost:8080/orders
curl http://localhost:8080/orders
curl http://localhost:8080/orders
curl http://localhost:8080/metrics
```

Expected `/orders` response:

```json
{
  "orders": [
    {
      "id": "ord-1001",
      "status": "paid"
    },
    {
      "id": "ord-1002",
      "status": "packed"
    },
    {
      "id": "ord-1003",
      "status": "shipped"
    }
  ]
}
```

## Step 6: View Traces in Jaeger

Port-forward Jaeger:

```bash
kubectl port-forward svc/jaeger 16686:16686 -n observability-demo
```

Open this URL:

```text
http://localhost:16686
```

In Jaeger:

1. Select service `orders-api`.
2. Click `Find Traces`.
3. Open one trace.
4. Look for spans such as `GET /orders` and `load_orders`.

If no traces appear, generate more traffic:

```bash
curl http://localhost:8080/orders
curl http://localhost:8080/orders
```

Then check collector logs:

```bash
kubectl logs deploy/otel-collector -n observability-demo
```

## Step 7: View Logs in Kibana

Port-forward Kibana:

```bash
kubectl port-forward svc/kibana 5601:5601 -n observability-demo
```

Open this URL:

```text
http://localhost:5601
```

Create a Kibana data view:

1. Go to `Stack Management`.
2. Select `Data Views`.
3. Create a data view.
4. Use index pattern:

```text
k8s-logs*
```

Then go to `Discover` and search for:

```text
orders loaded
```

## Step 8: Verify Elasticsearch Logs

Port-forward Elasticsearch:

```bash
kubectl port-forward svc/elasticsearch 9200:9200 -n observability-demo
```

In another terminal:

```bash
curl http://localhost:9200/_cat/indices?v
```

You should see an index similar to:

```text
k8s-logs
```

## Step 9: View Metrics with Prometheus and PromQL

Port-forward Prometheus:

```bash
kubectl port-forward svc/prometheus 9090:9090 -n observability-demo
```

Open:

```text
http://localhost:9090
```

Check targets:

```text
http://localhost:9090/targets
```

Practice PromQL:

```promql
orders_api_http_requests_total
```

```promql
sum(rate(orders_api_http_requests_total[1m])) by (endpoint)
```

```promql
histogram_quantile(0.95, sum(rate(orders_api_request_latency_seconds_bucket[5m])) by (le, endpoint))
```

## Step 10: View Loki Logs and Prometheus Metrics in Grafana

Port-forward Grafana:

```bash
kubectl port-forward svc/grafana 3000:3000 -n observability-demo
```

Open:

```text
http://localhost:3000
```

Login:

```text
username: admin
password: admin
```

Grafana has these data sources preconfigured:

- Prometheus
- Loki
- Jaeger

Open:

```text
Dashboards -> Observability Demo -> Orders API Metrics and Logs
```

In Grafana Explore, choose Loki and practice LogQL:

```logql
{app="orders-api"}
```

```logql
{namespace="observability-demo"}
```

```logql
{app="orders-api"} |= "orders loaded"
```

Check Loki directly:

```bash
kubectl port-forward svc/loki 3100:3100 -n observability-demo
curl http://localhost:3100/ready
```

## Step 11: Useful Debug Commands

Check app pods:

```bash
kubectl get pods -n observability-demo -l app=orders-api
```

Check app logs:

```bash
kubectl logs deploy/orders-api -n observability-demo
```

Check OpenTelemetry Collector:

```bash
kubectl logs deploy/otel-collector -n observability-demo
```

Check Jaeger:

```bash
kubectl logs deploy/jaeger -n observability-demo
```

Check Fluent Bit:

```bash
kubectl logs ds/fluent-bit -n observability-demo
```

Check Elasticsearch:

```bash
kubectl logs deploy/elasticsearch -n observability-demo
```

Check Kibana:

```bash
kubectl logs deploy/kibana -n observability-demo
```

Check Prometheus:

```bash
kubectl logs deploy/prometheus -n observability-demo
```

Check Grafana:

```bash
kubectl logs deploy/grafana -n observability-demo
```

Check Loki:

```bash
kubectl logs deploy/loki -n observability-demo
```

Check Promtail:

```bash
kubectl logs ds/promtail -n observability-demo
```

Describe a failing pod:

```bash
kubectl describe pod <pod-name> -n observability-demo
```

## Step 12: Clean Up

Delete the demo resources:

```bash
kubectl delete namespace observability-demo
```

Delete the Kind cluster:

```bash
kind delete cluster --name observability
```

## Optional: Use Argo CD to Deploy and Fix Errors

Argo CD support is included in:

```text
argocd/
```

Use it when you want to deploy this project from Git and practice fixing errors through GitOps sync.

Read:

```text
argocd/README.md
```

Basic flow:

```powershell
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl wait --for=condition=available deployment/argocd-server -n argocd --timeout=300s
```

Then edit:

```text
argocd/applications/observability-app.yaml
```

Replace:

```text
REPLACE_WITH_YOUR_GIT_REPO_URL
```

with your Git repo URL, then apply:

```powershell
kubectl apply -f .\argocd\applications\observability-app.yaml
```

Argo CD can fix manual drift, such as wrong service selectors, wrong readiness probes, or changed ConfigMaps, by syncing the desired state from Git.

## Common Issues

### ImagePullBackOff for `orders-api`

This usually means the image was not loaded into Kind.

Fix:

```bash
docker build -t orders-api:local ./app
kind load docker-image orders-api:local --name observability
kubectl rollout restart deployment/orders-api -n observability-demo
```

### Kibana or Elasticsearch Takes Too Long

Elasticsearch and Kibana need more memory than the demo app. If pods stay pending or crash, check Docker Desktop memory settings and give Docker at least 6 GB RAM.

Check status:

```bash
kubectl get pods -n observability-demo
kubectl describe pod -l app=elasticsearch -n observability-demo
kubectl describe pod -l app=kibana -n observability-demo
```

### No Traces in Jaeger

Generate traffic first:

```bash
curl http://localhost:8080/orders
curl http://localhost:8080/orders
```

Then check:

```bash
kubectl logs deploy/orders-api -n observability-demo
kubectl logs deploy/otel-collector -n observability-demo
kubectl logs deploy/jaeger -n observability-demo
```

### No Logs in Kibana

Check Fluent Bit and Elasticsearch:

```bash
kubectl logs ds/fluent-bit -n observability-demo
kubectl port-forward svc/elasticsearch 9200:9200 -n observability-demo
curl http://localhost:9200/_cat/indices?v
```

### No Metrics in Prometheus

Check the app metrics endpoint:

```bash
kubectl port-forward svc/orders-api 8080:8080 -n observability-demo
curl http://localhost:8080/metrics
```

Check Prometheus targets:

```text
http://localhost:9090/targets
```

Check Prometheus config:

```bash
kubectl get configmap prometheus-config -n observability-demo -o yaml
kubectl logs deploy/prometheus -n observability-demo
```

### No Logs in Loki

Generate traffic first:

```bash
curl http://localhost:8080/orders
```

Then check:

```bash
kubectl logs ds/promtail -n observability-demo
kubectl logs deploy/loki -n observability-demo
```

## Project Explanation

The `orders-api` service sends traces to the OpenTelemetry Collector using OTLP. The collector receives spans, batches them, and forwards them to Jaeger. Jaeger lets you inspect request latency and trace spans.

The application exposes Prometheus metrics at `/metrics`. Prometheus scrapes that endpoint, and Grafana lets you query the data with PromQL.

The application writes logs to stdout. Fluent Bit runs as a Kubernetes DaemonSet, reads container logs from the node, adds Kubernetes metadata, and sends them to Elasticsearch. Kibana connects to Elasticsearch so you can search and inspect those logs.

Promtail also reads pod logs and sends them to Loki. Grafana connects to Loki so you can query logs with LogQL. This gives you both EFK-style logging and Grafana/Loki-style logging in the same project.
