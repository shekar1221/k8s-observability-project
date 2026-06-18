# Latency Troubleshooting Runbook

Use this guide when someone says: "The application is slow."

In observability, do not start with random commands. Follow this order:

1. Confirm the application is reachable.
2. Measure latency from the client side.
3. Use Prometheus to find which service or endpoint is slow.
4. Use Jaeger to see where time is spent inside one request.
5. Use Loki or kubectl logs to find errors, retries, dependency failures, or slow database/cache calls.
6. Check Kubernetes health, resource pressure, and service endpoints.
7. Fix, redeploy, and confirm latency improved.

## Important Words

Latency means how long one request takes.

P95 latency means 95 percent of requests are faster than this value. If P95 is `2s`, then 5 percent of requests are slower than `2s`.

P99 latency means 99 percent of requests are faster than this value. P99 is useful for finding bad user experience even when average latency looks okay.

Throughput means how many requests per second the service handles.

Error rate means how many requests are failing with `4xx` or `5xx`.

## Step 1: Confirm Pods Are Running

```powershell
kubectl get pods -n observability-demo -o wide
```

Expected:

```text
READY   STATUS
1/1     Running
```

If a pod is not ready, describe it:

```powershell
kubectl describe pod -n observability-demo -l app=cart-api
```

Check recent events:

```powershell
kubectl get events -n observability-demo --sort-by=.lastTimestamp
```

## Step 2: Check Service Endpoints

If a Service has no endpoints, traffic cannot reach healthy pods.

Use EndpointSlice because old `endpoints` is deprecated in newer Kubernetes versions:

```powershell
kubectl get endpointslice -n observability-demo -l kubernetes.io/service-name=cart-api
```

Also check the Service selector and pod labels:

```powershell
kubectl get svc cart-api -n observability-demo -o yaml
kubectl get pods -n observability-demo -l app=cart-api --show-labels
```

The Service selector must match pod labels. Example:

```yaml
selector:
  app: cart-api
```

## Step 3: Measure Latency from Your Laptop

If using ingress:

```powershell
curl.exe -w "time_total=%{time_total}s status=%{http_code}`n" -o NUL -s http://shop.observability.local/home
curl.exe -w "time_total=%{time_total}s status=%{http_code}`n" -o NUL -s http://shop.observability.local/checkout-demo
```

If using port-forward:

```powershell
kubectl port-forward svc/frontend 8080:8080 -n observability-demo
```

Open another terminal:

```powershell
curl.exe -w "time_total=%{time_total}s status=%{http_code}`n" -o NUL -s http://localhost:8080/home
curl.exe -w "time_total=%{time_total}s status=%{http_code}`n" -o NUL -s http://localhost:8080/checkout-demo
```

If `time_total` is high, the user-facing request is slow.

## Step 4: Generate Traffic for Metrics and Traces

Prometheus, Loki, and Jaeger need traffic before they show useful data.

PowerShell loop:

```powershell
1..30 | ForEach-Object {
  curl.exe -s http://shop.observability.local/home | Out-Null
  curl.exe -s http://shop.observability.local/checkout-demo | Out-Null
}
```

Port-forward version:

```powershell
1..30 | ForEach-Object {
  curl.exe -s http://localhost:8080/home | Out-Null
  curl.exe -s http://localhost:8080/checkout-demo | Out-Null
}
```

If a LoadBalancer (LB) is installed and working, you usually do not need port-forward.
Use LoadBalancer when your frontend service has an external IP or hostname:
kubectl get svc -n three-tier
Look for something like:
frontend   LoadBalancer   10.x.x.x   34.x.x.x.x   80:xxxxx/TCP
Then generate traffic using the external IP:
```
for i in {1..30}; do
  curl -s http://EXTERNAL-IP/home > /dev/null
  curl -s http://EXTERNAL-IP/checkout-demo > /dev/null
done
```
Example:
```
for i in {1..30}; do
  curl -s http://34.120.10.50/home > /dev/null
  curl -s http://34.120.10.50/checkout-demo > /dev/null
done
```
Use port-forward only if:
the service is ClusterIP
LoadBalancer external IP is still <pending>
you are testing locally
DNS like shop.observability.local is not configured
To check:
kubectl get svc -n three-tier
If frontend has a real EXTERNAL-IP, use LB.
If it says <pending>, use port-forward:
kubectl port-forward svc/frontend 8080:80 -n three-tier
Use the LoadBalancer URL/IP.
Run this first:
kubectl get svc -n three-tier
Find the frontend service and copy the EXTERNAL-IP.
Then run traffic like this:
```
for i in {1..30}; do
  curl -s http://EXTERNAL-IP/home > /dev/null
  curl -s http://EXTERNAL-IP/checkout-demo > /dev/null
done
Example:
for i in {1..30}; do
  curl -s http://34.120.10.50/home > /dev/null
  curl -s http://34.120.10.50/checkout-demo > /dev/null
done
If you have DNS configured:
for i in {1..30}; do
  curl -s http://shop.observability.local/home > /dev/null
  curl -s http://shop.observability.local/checkout-demo > /dev/null
done
```
Do not use port-forward if the LoadBalancer external IP is working.

## Step 5: Open Prometheus

```powershell
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

All targets should be `UP`.

## Step 6: Find the Slowest Service with PromQL

Paste this in Prometheus:

```promql
topk(10, histogram_quantile(0.95, sum by (le, __name__, endpoint) (rate({__name__=~".*_request_latency_seconds_bucket"}[5m]))))
```

What it means:

- `rate(...[5m])` checks the last 5 minutes.
- `histogram_quantile(0.95, ...)` calculates P95 latency.
- `topk(10, ...)` shows the slowest results first.

Service-specific examples:

```promql
histogram_quantile(0.95, sum(rate(frontend_request_latency_seconds_bucket[5m])) by (le, endpoint))
```

```promql
histogram_quantile(0.95, sum(rate(cart_api_request_latency_seconds_bucket[5m])) by (le, endpoint))
```

```promql
histogram_quantile(0.95, sum(rate(orders_api_request_latency_seconds_bucket[5m])) by (le, endpoint))
```

If `cart-api` has high latency, continue with cart-api logs and traces.

## Step 7: Check Error Rate

Latency and errors often happen together.

```promql
sum by (__name__, endpoint, status) (rate({__name__=~".*_http_requests_total",status=~"4..|5.."}[5m]))
```

Check frontend request rate:

```promql
sum(rate(frontend_http_requests_total[5m])) by (endpoint, status)
```

Check cart API request rate:

```promql
sum(rate(cart_api_http_requests_total[5m])) by (endpoint, status)
```

If you see many `5xx` responses, check logs immediately.

## Step 8: Check Logs with kubectl

Start with the slow service:

```powershell
kubectl logs deploy/cart-api -n observability-demo --tail=100
```

Follow live logs:

```powershell
kubectl logs deploy/cart-api -n observability-demo -f
```

Look for:

```text
latency_ms=
redis unavailable
mysql unavailable
timeout
error
```

Check frontend logs too, because frontend calls other services:

```powershell
kubectl logs deploy/frontend -n observability-demo --tail=100
```

## Step 9: Check Logs with Loki in Grafana

Port-forward Grafana:

```powershell
kubectl port-forward svc/grafana 3000:3000 -n observability-demo
```

Open:

```text
http://localhost:3000
```

Go to:

```text
Explore -> Loki
```

Useful LogQL queries:

```logql
{namespace="observability-demo"}
```

```logql
{app="cart-api"} |= "latency_ms"
```

```logql
{app="cart-api"} |= "redis unavailable"
```

```logql
{app="frontend"} |= "checkout demo"
```

```logql
{namespace="observability-demo"} |= "error"
```

If Loki returns no data:

```powershell
kubectl get pods -n observability-demo -l app=promtail
kubectl logs ds/promtail -n observability-demo --tail=100
kubectl logs deploy/loki -n observability-demo --tail=100
```

## Step 10: Use Jaeger to Find the Slow Span

Port-forward Jaeger:

```powershell
kubectl port-forward svc/jaeger 16686:16686 -n observability-demo
```

Open:

```text
http://localhost:16686
```

In Jaeger:

1. Select service `frontend`.
2. Click `Find Traces`.
3. Sort by longest duration.
4. Open a slow trace.
5. Look for the span that takes the most time.

If `frontend` is slow and `cart-api` span is long, the issue is likely in cart-api or Redis.

Check collector logs if traces are missing:

```powershell
kubectl logs deploy/otel-collector -n observability-demo --tail=100
kubectl logs deploy/jaeger -n observability-demo --tail=100
```

## Step 11: Check CPU and Memory Pressure

This requires metrics-server. If it is installed:

```powershell
kubectl top pods -n observability-demo
kubectl top pod -n observability-demo -l app=cart-api
kubectl top nodes
```

If `kubectl top` does not work, use describe:

```powershell
kubectl describe pod -n observability-demo -l app=cart-api
```

Look for:

```text
OOMKilled
Back-off restarting failed container
Readiness probe failed
Liveness probe failed
CPU throttling symptoms
```

## Step 12: Check Dependencies

For cart-api, check Redis:

```powershell
kubectl get pods -n observability-demo -l app=redis
kubectl logs deploy/redis -n observability-demo --tail=100
kubectl exec deploy/redis -n observability-demo -- redis-cli ping
```

For user-api, check MySQL:

```powershell
kubectl get pods -n observability-demo -l app=mysql
kubectl logs deploy/mysql -n observability-demo --tail=100
kubectl exec deploy/mysql -n observability-demo -- mysqladmin ping -h 127.0.0.1 -uroot -prootpass
```

Expected:

```text
PONG
mysqld is alive
```

## Step 13: Practice a Real Latency Issue

This project includes a latency lab that makes `cart-api` slower.

Apply the lab:

```powershell
kubectl apply -k .\troubleshooting-labs\04-latency-cart-api
kubectl rollout status deployment/cart-api -n observability-demo
```

Generate traffic:

```powershell
1..30 | ForEach-Object {
  curl.exe -s http://shop.observability.local/checkout-demo | Out-Null
}
```

Find it in Prometheus:

```promql
topk(10, histogram_quantile(0.95, sum by (le, __name__, endpoint) (rate({__name__=~".*_request_latency_seconds_bucket"}[5m]))))
```

You should see `cart_api_request_latency_seconds_bucket` become slow.

Find it in logs:

```powershell
kubectl logs deploy/cart-api -n observability-demo --tail=100
```

Fix the lab by applying the normal project again:

```powershell
kubectl apply -k .\k8s
kubectl rollout status deployment/cart-api -n observability-demo
```

Confirm latency improves by running the PromQL query again.

## Step 14: Common Fixes

If one pod is overloaded, scale it:

```powershell
kubectl scale deployment/cart-api -n observability-demo --replicas=2
```

If the latest change caused latency, rollback:

```powershell
kubectl rollout undo deployment/cart-api -n observability-demo
kubectl rollout status deployment/cart-api -n observability-demo
```

If resources are too low, edit requests and limits in the YAML:

```text
k8s/46-shopping-services.yaml
```

Then apply:

```powershell
kubectl apply -k .\k8s
```

If dependency is slow, check dependency pod, logs, readiness, and connection errors.

## Interview Explanation

Use this answer:

```text
When users report latency, I first confirm pod and service health. Then I measure client-side latency using curl. After that I use Prometheus P95/P99 latency queries to identify which service and endpoint are slow. Once I know the slow service, I open a Jaeger trace to see which span or downstream dependency is consuming time. I use Loki or kubectl logs to verify errors, timeouts, retries, or dependency issues. Finally I check Kubernetes resources, endpoints, readiness probes, and dependent systems like Redis or MySQL. After applying the fix, I compare Prometheus latency before and after the change.
```
