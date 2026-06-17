# Interview Preparation Guide

Use this document to explain the project confidently in an interview.

## 30-Second Introduction

```text
I built a Kubernetes observability project on a local Kind cluster. It runs a shopping-cart style microservices application with frontend, user, cart, orders, payment, and shipping services. Redis is used for cart data and MySQL is used for user-style relational data. I instrumented the services with OpenTelemetry, Prometheus metrics, logs, and health checks. Traces go to Jaeger, metrics go to Prometheus and Grafana, and logs go to both EFK and Loki. I also added Argo CD for GitOps deployment and troubleshooting labs for real issues like ImagePullBackOff, service selector problems, and latency.
```

## 2-Minute Project Explanation

```text
The goal of this project was to learn how production teams observe and troubleshoot microservices on Kubernetes.

The application is a shopping platform. A user hits the frontend service, and the frontend calls backend services like cart-api, user-api, orders-api, payment-api, and shipping-api. Redis supports cart data, and MySQL supports relational user data.

For observability, each service exposes /healthz and /metrics. Prometheus scrapes metrics, and Grafana visualizes latency, request rate, and logs. Each service exports traces using OpenTelemetry to the OpenTelemetry Collector, and the collector sends traces to Jaeger. Logs are written to stdout, collected by Fluent Bit into Elasticsearch/Kibana, and also collected by Promtail into Loki for Grafana LogQL queries.

I deployed it on Kind so I could practice locally. I also added NGINX ingress so I can access services with hostnames instead of always using port-forward. I included Argo CD so the same manifests can be deployed through GitOps and automatically corrected if someone manually changes Kubernetes objects.
```

## Architecture Explanation

Say it like this:

```text
The request starts from the browser or curl. It reaches NGINX ingress, then the frontend service. The frontend calls downstream services. Each service produces three observability signals: metrics, logs, and traces. Metrics go to Prometheus, logs go to Loki and EFK, and traces go through OpenTelemetry Collector to Jaeger. Grafana is the single place where I can view Prometheus metrics, Loki logs, and Jaeger traces.
```

## What I Personally Worked On

Use these points:

- Created Kubernetes manifests for the application and observability stack.
- Built local Docker images and loaded them into the Kind cluster.
- Added readiness and liveness probes using `/healthz`.
- Added Prometheus `/metrics` endpoints.
- Added OpenTelemetry tracing.
- Added Grafana data sources and dashboards.
- Added Loki and Promtail for logs.
- Added NGINX ingress for browser access.
- Added Argo CD applications for GitOps deployment.
- Added troubleshooting labs to intentionally create and fix issues.

## Issues I Faced and Fixed

### 1. Docker Desktop Was Not Running

Problem:

```text
kind delete cluster failed because Docker API was not reachable.
```

What I checked:

```powershell
docker ps -a
docker context ls
```

Root cause:

```text
Docker Desktop Linux engine was not running, so Kind could not talk to Docker.
```

Fix:

```powershell
docker context use desktop-linux
docker ps
kind get clusters
```

How to explain:

```text
Kind runs Kubernetes nodes as Docker containers, so if Docker Desktop is down, Kind commands fail. I checked Docker context and restarted/selected the Docker Desktop Linux context.
```

### 2. ImagePullBackOff for Local Images

Problem:

```text
Pods tried to pull orders-api:local from Docker Hub and failed.
```

Command:

```powershell
kubectl describe pod -n observability-demo -l app=orders-api
```

Root cause:

```text
The image existed on my laptop but not inside the Kind node.
```

Fix:

```powershell
docker build -t orders-api:local .\app
kind load docker-image orders-api:local --name observability
kubectl rollout restart deployment/orders-api -n observability-demo
```

How to explain:

```text
For Kind, local Docker images are not automatically available inside the cluster node. I built the image locally, loaded it into Kind, and restarted the deployment.
```

### 3. CrashLoopBackOff Due to Missing Python Dependency

Problem:

```text
orders-api crashed with ModuleNotFoundError: No module named 'pkg_resources'
```

Command:

```powershell
kubectl logs deploy/orders-api -n observability-demo --previous
```

Root cause:

```text
The Python image did not include the package needed by OpenTelemetry instrumentation.
```

Fix:

```text
Updated the Dockerfile/requirements to install setuptools/wheel and rebuilt the image.
```

Commands:

```powershell
docker build --no-cache -t orders-api:local .\app
kind load docker-image orders-api:local --name observability
kubectl rollout restart deployment/orders-api -n observability-demo
```

How to explain:

```text
I used pod logs to find the Python import error, fixed the container dependencies, rebuilt the image without cache, loaded it into Kind, and restarted the deployment.
```

### 4. Ingress Returned 503

Problem:

```text
NGINX ingress returned 503 Service Temporarily Unavailable.
```

Commands:

```powershell
kubectl get pods -n observability-demo -l app=orders-api
kubectl get svc orders-api -n observability-demo
kubectl get endpointslice -n observability-demo -l kubernetes.io/service-name=orders-api
```

Root cause:

```text
Service had no endpoints because pods were not ready or the service selector did not match pod labels.
```

Fix example:

```powershell
kubectl patch svc orders-api -n observability-demo --type merge -p '{"spec":{"selector":{"app":"orders-api"}}}'
```

How to explain:

```text
Ingress sends traffic to a Kubernetes Service. If the Service has no endpoints, ingress returns 503. I checked pods, service selector, and EndpointSlices to confirm whether traffic had healthy backend pods.
```

### 5. Loki Dashboard Had No Data

Problem:

```text
Grafana Loki dashboard showed no logs.
```

Commands:

```powershell
kubectl get pods -n observability-demo -l app=promtail
kubectl logs ds/promtail -n observability-demo --tail=100
kubectl logs deploy/loki -n observability-demo --tail=100
```

Root cause possibilities:

```text
No traffic generated, Promtail not scraping pod logs, label query mismatch, or Loki not ready.
```

Fix:

```powershell
curl.exe http://shop.observability.local/home
curl.exe http://shop.observability.local/checkout-demo
```

Then query:

```logql
{namespace="observability-demo"}
```

How to explain:

```text
For logs to appear in Loki, the app must produce stdout logs, Promtail must scrape them, and Grafana must query the correct labels. I checked Promtail, Loki, generated traffic, and then used a broad LogQL query before narrowing to app-specific labels.
```

### 6. Latency Issue in cart-api

Problem:

```text
Checkout flow became slow.
```

Commands:

```powershell
curl.exe -w "time_total=%{time_total}s status=%{http_code}`n" -o NUL -s http://shop.observability.local/checkout-demo
```

PromQL:

```promql
topk(10, histogram_quantile(0.95, sum by (le, __name__, endpoint) (rate({__name__=~".*_request_latency_seconds_bucket"}[5m]))))
```

Logs:

```powershell
kubectl logs deploy/cart-api -n observability-demo --tail=100
```

Jaeger:

```text
Open Jaeger -> choose frontend -> find traces -> sort by duration -> open slow trace.
```

How to explain:

```text
I first measured user-facing latency, then used Prometheus P95 latency to identify the slow service. After that I checked Jaeger traces to see which span was slow, and logs to confirm whether Redis, code latency, or downstream calls were the cause.
```

## Observability Scenarios and What to Check

### Scenario 1: User says the app is slow

Check:

```powershell
kubectl get pods -n observability-demo
curl.exe -w "time_total=%{time_total}s status=%{http_code}`n" -o NUL -s http://shop.observability.local/home
```

PromQL:

```promql
topk(10, histogram_quantile(0.95, sum by (le, __name__, endpoint) (rate({__name__=~".*_request_latency_seconds_bucket"}[5m]))))
```

Then:

```text
Open Jaeger and inspect the longest trace.
```

### Scenario 2: App returns 503

Check:

```powershell
kubectl get ingress -n observability-demo
kubectl get svc -n observability-demo
kubectl get endpointslice -n observability-demo
kubectl describe ingress shopping-platform-ingress -n observability-demo
```

Most likely causes:

```text
No ready pods, wrong service selector, wrong service port, or ingress controller not ready.
```

### Scenario 3: Pod is CrashLoopBackOff

Check:

```powershell
kubectl get pods -n observability-demo
kubectl logs <pod-name> -n observability-demo --previous
kubectl describe pod <pod-name> -n observability-demo
```

Most likely causes:

```text
Bad image, missing dependency, wrong environment variable, application exception, failed health check.
```

### Scenario 4: Prometheus target is down

Check:

```powershell
kubectl port-forward svc/prometheus 9090:9090 -n observability-demo
```

Open:

```text
http://localhost:9090/targets
```

Then check service reachability:

```powershell
kubectl get svc -n observability-demo
kubectl port-forward svc/cart-api 8081:8080 -n observability-demo
curl.exe http://localhost:8081/metrics
```

Most likely causes:

```text
Wrong service name, wrong port, app not exposing /metrics, or pod not ready.
```

### Scenario 5: Traces missing in Jaeger

Check:

```powershell
kubectl logs deploy/otel-collector -n observability-demo --tail=100
kubectl logs deploy/jaeger -n observability-demo --tail=100
kubectl get svc otel-collector jaeger -n observability-demo
```

Most likely causes:

```text
Wrong OTEL_EXPORTER_OTLP_ENDPOINT, collector config issue, app not instrumented, or no traffic generated.
```

### Scenario 6: Logs missing in Loki

Check:

```powershell
kubectl logs ds/promtail -n observability-demo --tail=100
kubectl logs deploy/loki -n observability-demo --tail=100
```

Broad LogQL first:

```logql
{namespace="observability-demo"}
```

Then narrow:

```logql
{app="cart-api"} |= "latency_ms"
```

### Scenario 7: Argo CD shows OutOfSync because of drift

Meaning:

```text
Drift means the live Kubernetes state is different from the desired state stored in Git.
```

Example:

```text
In Git, the orders-api Service selector is app=orders-api.
Someone manually patches the live Service selector to app=wrong-app.
Now pods are running, but the Service has no healthy endpoints.
Ingress can return 503.
Argo CD shows the application as OutOfSync.
```

Create drift for practice:

```powershell
kubectl patch svc orders-api -n observability-demo --type merge -p '{"spec":{"selector":{"app":"wrong-app"}}}'
```

Check the issue:

```powershell
kubectl get svc orders-api -n observability-demo -o yaml
kubectl get pods -n observability-demo -l app=orders-api --show-labels
kubectl get endpointslice -n observability-demo -l kubernetes.io/service-name=orders-api
kubectl get applications -n argocd
```

Expected symptom:

```text
orders-api Service has no endpoints.
Argo CD application becomes OutOfSync.
Ingress may return 503.
```

Handle it with Argo CD:

```powershell
kubectl annotate application observability-stack -n argocd argocd.argoproj.io/refresh=hard --overwrite
```

Then sync from Argo CD UI:

```text
Argo CD UI -> observability-stack -> Sync
```

Or use CLI if installed:

```powershell
argocd app sync observability-stack
```

Verify after sync:

```powershell
kubectl get svc orders-api -n observability-demo -o yaml
kubectl get endpointslice -n observability-demo -l kubernetes.io/service-name=orders-api
kubectl get applications -n argocd
```

Production handling:

```text
Do not rely only on manual sync. Use RBAC to restrict direct kubectl changes, require pull requests for production changes, enable Argo CD self-heal where appropriate, and monitor OutOfSync applications.
```

## Interview Questions and Answers

### What is observability?

Observability is the ability to understand what is happening inside a system by looking at its external signals: metrics, logs, and traces.

### What are metrics?

Metrics are numeric time-series data. Examples are request count, error rate, latency, CPU, and memory.

### What are logs?

Logs are event records from applications or infrastructure. They help explain what happened at a specific time.

### What are traces?

Traces show the full path of a request across services. They help identify which service or span caused latency.

### Why do we need Prometheus?

Prometheus scrapes metrics from services and stores time-series data. I use it to query request rate, error rate, and latency using PromQL.

### Why do we need Grafana?

Grafana visualizes metrics and logs. In this project, Grafana connects to Prometheus, Loki, and Jaeger.

### Why do we need Jaeger?

Jaeger is used for distributed tracing. It helps me find where a request spent time across frontend, cart, payment, shipping, and orders services.

### Why do we need OpenTelemetry?

OpenTelemetry is a standard way to instrument applications and collect traces, metrics, and logs. In this project, app traces go to the OpenTelemetry Collector, then to Jaeger.

### Why do we need Loki if we already have EFK?

EFK is a common Elasticsearch-based logging stack. Loki is lighter and integrates very well with Grafana. I included both to learn both logging approaches.

### What is the difference between readiness and liveness probes?

Readiness tells Kubernetes whether a pod can receive traffic. Liveness tells Kubernetes whether the container should be restarted.

### Why did ingress return 503?

Ingress returned 503 because the backend service had no healthy endpoints. That can happen when pods are not ready or when the service selector does not match pod labels.

### What is ImagePullBackOff?

ImagePullBackOff means Kubernetes could not pull the container image. In Kind, this often happens when a local image was built on the laptop but not loaded into the Kind node.

### How do you troubleshoot latency?

I measure client latency, check Prometheus P95/P99 latency, identify the slow service, inspect Jaeger traces for slow spans, check logs in Loki or kubectl, then check Kubernetes resources and dependencies.

### What is P95 latency?

P95 latency means 95 percent of requests are faster than that value. It is more useful than average because average can hide slow user experiences.

### What is RED method?

RED means Rate, Errors, and Duration. It is useful for service-level monitoring.

### What is USE method?

USE means Utilization, Saturation, and Errors. It is useful for infrastructure resources like CPU, memory, disk, and network.

### Why use Argo CD?

Argo CD continuously compares Kubernetes actual state with Git desired state. If someone manually changes a service or deployment, Argo CD can show drift and sync it back.

### What is drift in Kubernetes GitOps?

Drift means the actual live Kubernetes state is different from the desired state stored in Git. For example, Git may define a Service selector as `app=orders-api`, but someone manually changes the live selector to `app=wrong-app` using `kubectl patch`. The pods may still be running, but the Service has no endpoints and ingress can return 503. Argo CD detects this as `OutOfSync`. I would compare live versus desired state, sync the application back from Git, and prevent future drift with RBAC, pull-request based changes, and Argo CD self-heal where suitable.

### How do you troubleshoot an Argo CD OutOfSync application?

I first check the application:

```powershell
kubectl get applications -n argocd
kubectl describe application observability-stack -n argocd
```

Then I compare the live object with Git desired state. If the change was manual and not approved, I sync from Argo CD:

```powershell
argocd app sync observability-stack
```

If I do not have Argo CD CLI, I use the UI:

```text
Argo CD UI -> Application -> Diff -> Sync
```

After sync, I verify the Kubernetes object and application health:

```powershell
kubectl get applications -n argocd
kubectl get pods -n observability-demo
```

### What is GitOps?

GitOps means Git is the source of truth for infrastructure and application deployment. Changes are made through Git commits, and Argo CD applies them to Kubernetes.

## Python Coding Questions They May Ask

### 1. Write Python code to check API latency

Write this:

```python
import time
from urllib.request import urlopen


def check_latency(url):
    start = time.perf_counter()
    with urlopen(url, timeout=5) as response:
        response.read()
        latency_ms = (time.perf_counter() - start) * 1000
        return response.status, round(latency_ms, 2)


status, latency = check_latency("http://localhost:8080/healthz")
print(status, latency)
```

How to explain:

```text
I use perf_counter because it is good for measuring elapsed time. I call the URL, read the response, calculate elapsed milliseconds, and return status plus latency.
```

Full runnable file:

```text
interview-code/latency_checker.py
```

### 2. Write Python code to parse latency from logs

Write this:

```python
import re

line = "checkout completed order_id=123 latency_ms=250"
match = re.search(r"latency_ms=(\d+)", line)
if match:
    print(int(match.group(1)))
```

How to explain:

```text
Many application logs include fields like latency_ms. I can extract those values and calculate min, max, average, and P95.
```

Full runnable file:

```text
interview-code/log_latency_parser.py
```

### 3. Write a Flask health check

Write this:

```python
from flask import Flask

app = Flask(__name__)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
```

How to explain:

```text
Kubernetes readiness and liveness probes can call /healthz to decide whether the pod is healthy and ready for traffic.
```

### 4. Write Python code with Prometheus metrics

Write this:

```python
from flask import Flask, Response
from prometheus_client import Counter, generate_latest

app = Flask(__name__)
REQUESTS = Counter("demo_requests_total", "Total demo requests")


@app.get("/")
def home():
    REQUESTS.inc()
    return {"message": "ok"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), mimetype="text/plain")
```

How to explain:

```text
Prometheus scrapes the /metrics endpoint. The counter increases every time the app receives a request.
```

### 5. Write Python retry logic

Write this:

```python
import time
from urllib.error import URLError
from urllib.request import urlopen


def get_with_retry(url, attempts=3):
    for attempt in range(1, attempts + 1):
        try:
            with urlopen(url, timeout=3) as response:
                return response.status
        except URLError:
            if attempt == attempts:
                raise
            time.sleep(attempt)
```

How to explain:

```text
Retries help with temporary network failures, but too many retries can increase latency and load. In production I would also add timeouts, logging, and metrics.
```

## How to Present Yourself

Use this structure:

```text
I am learning and building hands-on Kubernetes observability projects. I understand the basics of deploying services, checking pod health, debugging ImagePullBackOff and CrashLoopBackOff, and using Prometheus, Grafana, Loki, Jaeger, and OpenTelemetry to troubleshoot real issues. I may not know every production tool deeply yet, but I know how to investigate systematically: check Kubernetes state, confirm endpoints, inspect logs, use metrics to find the failing service, use traces to identify slow dependencies, and validate the fix.
```

## Strong Closing Statement

```text
This project helped me understand observability practically. I did not just deploy tools; I created failure scenarios and fixed them. That helped me learn how production troubleshooting works: start from symptoms, check service health, use metrics to locate the issue, use traces to understand request flow, use logs to explain the root cause, then apply and verify the fix.
```
