# Kubernetes Troubleshooting Labs

These labs intentionally break the EFK observability project so you can practice troubleshooting.

The base working project is still in:

```text
k8s/
```

Each lab is a Kustomize overlay that applies the base manifests plus one bad YAML patch.

## Reset to Working State

Use this before moving between labs:

```powershell
kubectl delete namespace observability-demo
kubectl apply -k .\k8s
```

If you use Kind and the app image is missing:

```powershell
docker build -t orders-api:local .\app
kind load docker-image orders-api:local --name observability
kubectl rollout restart deployment/orders-api -n observability-demo
```

## Lab 1: ImagePullBackOff

Creates a wrong image name for `orders-api`.

Apply:

```powershell
kubectl delete namespace observability-demo
kubectl apply -k .\troubleshooting-labs\01-imagepullbackoff
kubectl get pods -n observability-demo
```

Expected symptom:

```text
orders-api ... ImagePullBackOff
```

Troubleshoot:

```powershell
kubectl describe pod -l app=orders-api -n observability-demo
kubectl get events -n observability-demo --sort-by=.lastTimestamp
```

Fix:

```powershell
kubectl set image deployment/orders-api orders-api=orders-api:local -n observability-demo
```

## Lab 2: Service Selector Mismatch / Ingress 503

Breaks the `orders-api` Service selector so it does not match the pods.

Apply:

```powershell
kubectl delete namespace observability-demo
kubectl apply -k .\troubleshooting-labs\02-service-selector-503
kubectl get endpoints orders-api -n observability-demo
```

Expected symptom:

```text
ENDPOINTS empty
```

If using Ingress, this usually causes:

```text
503 Service Temporarily Unavailable
```

Troubleshoot:

```powershell
kubectl get pods -n observability-demo --show-labels
kubectl describe svc orders-api -n observability-demo
kubectl get endpoints orders-api -n observability-demo
```

Fix:

```powershell
kubectl patch svc orders-api -n observability-demo --type merge -p '{"spec":{"selector":{"app":"orders-api"}}}'
```

PowerShell escaping alternative:

```powershell
kubectl patch svc orders-api -n observability-demo --type merge -p '{\"spec\":{\"selector\":{\"app\":\"orders-api\"}}}'
```

## Lab 3: Readiness Probe Failure

Changes the readiness probe path from `/healthz` to `/wrong-healthz`.

Apply:

```powershell
kubectl delete namespace observability-demo
kubectl apply -k .\troubleshooting-labs\03-readiness-probe-failure
kubectl get pods -n observability-demo -l app=orders-api
```

Expected symptom:

```text
orders-api ... 0/1 Running
```

Troubleshoot:

```powershell
kubectl describe pod -l app=orders-api -n observability-demo
kubectl logs deploy/orders-api -n observability-demo
kubectl get endpoints orders-api -n observability-demo
```

Fix:

```powershell
kubectl patch deployment orders-api -n observability-demo --type json -p '[{"op":"replace","path":"/spec/template/spec/containers/0/readinessProbe/httpGet/path","value":"/healthz"}]'
```

## Lab 4: No Traces in Jaeger

Changes `OTEL_EXPORTER_OTLP_ENDPOINT` to a wrong service name.

Apply:

```powershell
kubectl delete namespace observability-demo
kubectl apply -k .\troubleshooting-labs\04-no-traces
curl http://localhost:8080/orders
```

Expected symptom:

```text
App works, but traces do not show in Jaeger.
```

Troubleshoot:

```powershell
kubectl logs deploy/orders-api -n observability-demo
kubectl logs deploy/otel-collector -n observability-demo
kubectl get svc -n observability-demo
```

Fix:

```powershell
kubectl set env deployment/orders-api OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317 -n observability-demo
```

## Lab 5: Kibana Cannot Reach Elasticsearch

Changes Kibana's `ELASTICSEARCH_HOSTS` to a wrong service name.

Apply:

```powershell
kubectl delete namespace observability-demo
kubectl apply -k .\troubleshooting-labs\05-kibana-no-elasticsearch
kubectl logs deploy/kibana -n observability-demo
```

Expected symptom:

```text
Kibana pod may run, but UI is unhealthy or logs show Elasticsearch connection errors.
```

Troubleshoot:

```powershell
kubectl get svc elasticsearch -n observability-demo
kubectl logs deploy/kibana -n observability-demo
kubectl port-forward svc/elasticsearch 9200:9200 -n observability-demo
curl http://localhost:9200
```

Fix:

```powershell
kubectl set env deployment/kibana ELASTICSEARCH_HOSTS=http://elasticsearch:9200 -n observability-demo
```

## Lab 6: YAML Syntax Error

This lab contains a deliberately invalid YAML file. Do not apply it to the cluster as a real deployment.

Run:

```powershell
kubectl apply -f .\troubleshooting-labs\06-yaml-syntax-error\broken-yaml.yaml
```

Expected symptom:

```text
error parsing ... did not find expected key
```

Fix by correcting indentation and adding the missing colon.

## Lab 7: Prometheus Target Down

Changes Prometheus scraping from `/metrics` to `/wrong-metrics`.

Apply:

```powershell
kubectl delete namespace observability-demo
kubectl apply -k .\troubleshooting-labs\07-prometheus-target-down
kubectl port-forward svc/prometheus 9090:9090 -n observability-demo
```

Open:

```text
http://localhost:9090/targets
```

Expected symptom:

```text
orders-api target is DOWN or returns HTTP 404
```

Troubleshoot:

```powershell
kubectl port-forward svc/orders-api 8080:8080 -n observability-demo
curl http://localhost:8080/metrics
kubectl get configmap prometheus-config -n observability-demo -o yaml
kubectl logs deploy/prometheus -n observability-demo
```

Fix by resetting to the working manifests:

```powershell
kubectl delete namespace observability-demo
kubectl apply -k .\k8s
```

Practice PromQL:

```promql
orders_api_http_requests_total
sum(rate(orders_api_http_requests_total[1m])) by (endpoint)
histogram_quantile(0.95, sum(rate(orders_api_request_latency_seconds_bucket[5m])) by (le, endpoint))
```

## Lab 8: Loki Logs Missing

Changes Promtail's Loki URL to a wrong service name.

Apply:

```powershell
kubectl delete namespace observability-demo
kubectl apply -k .\troubleshooting-labs\08-loki-logs-missing
kubectl logs ds/promtail -n observability-demo
```

Expected symptom:

```text
Promtail logs show connection or DNS errors for loki-wrong.
Grafana Loki query returns no logs.
```

Troubleshoot:

```powershell
kubectl get svc loki -n observability-demo
kubectl logs ds/promtail -n observability-demo
kubectl port-forward svc/grafana 3000:3000 -n observability-demo
```

In Grafana Explore, choose Loki and run:

```logql
{app="orders-api"}
{namespace="observability-demo"}
{app="orders-api"} |= "orders loaded"
```

Fix by resetting to the working manifests:

```powershell
kubectl delete namespace observability-demo
kubectl apply -k .\k8s
```

## Best Debug Order

Use this sequence for most issues:

```powershell
kubectl config current-context
kubectl get ns
kubectl get pods -n observability-demo
kubectl get svc -n observability-demo
kubectl get endpoints -n observability-demo
kubectl describe pod <pod-name> -n observability-demo
kubectl logs <pod-name> -n observability-demo
kubectl get events -n observability-demo --sort-by=.lastTimestamp
```
