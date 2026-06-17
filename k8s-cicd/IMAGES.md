# Required Images

For local Kind, these images must exist in the Kind node:

| Component | Local image |
|---|---|
| frontend | `shopping-frontend:local` |
| user-api | `user-api:local` |
| cart-api | `cart-api:local` |
| orders-api | `orders-api:local` |
| payment-api | `payment-api:local` |
| shipping-api | `shipping-api:local` |

Build and load them with:

```powershell
.\scripts\build-load-kind.ps1
```

Or Git Bash/Linux:

```bash
./scripts/build-load-kind.sh
```

External images pulled from public registries:

| Component | Image |
|---|---|
| MySQL | `mysql:8.4` |
| Redis | `redis:7-alpine` |
| Jaeger | `jaegertracing/all-in-one:1.57` |
| OpenTelemetry Collector | `otel/opentelemetry-collector-contrib:0.101.0` |
| Elasticsearch | `docker.elastic.co/elasticsearch/elasticsearch:8.13.4` |
| Kibana | `docker.elastic.co/kibana/kibana:8.13.4` |
| Fluent Bit | `fluent/fluent-bit:3.0` |
| Prometheus | `prom/prometheus:v2.52.0` |
| Loki | `grafana/loki:3.0.0` |
| Promtail | `grafana/promtail:3.0.0` |
| Grafana | `grafana/grafana:11.0.0` |
