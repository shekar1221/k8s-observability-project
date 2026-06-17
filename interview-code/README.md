# Python Interview Coding Examples

These examples are small enough to write on screenshare and still connect directly to this Kubernetes observability project.

## 1. Check API Latency

```powershell
python .\interview-code\latency_checker.py http://shop.observability.local/home http://shop.observability.local/checkout-demo
```

If you use port-forward:

```powershell
python .\interview-code\latency_checker.py http://localhost:8080/home http://localhost:8080/checkout-demo
```

## 2. Parse latency_ms from logs

```powershell
kubectl logs deploy/cart-api -n observability-demo --tail=200 | python .\interview-code\log_latency_parser.py
```

## 3. Show Flask Observability Basics

```powershell
python .\interview-code\flask_observability_sample.py
```

Then open:

```text
http://localhost:8080/healthz
http://localhost:8080/work
http://localhost:8080/metrics
```
