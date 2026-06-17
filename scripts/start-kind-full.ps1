param(
  [string]$ClusterName = "observability"
)

$ErrorActionPreference = "Stop"

kind create cluster --config .\kind-config.yaml
kubectl config use-context "kind-$ClusterName"

kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.11.1/deploy/static/provider/kind/deploy.yaml
kubectl wait --namespace ingress-nginx --for=condition=ready pod --selector=app.kubernetes.io/component=controller --timeout=180s

.\scripts\build-load-kind.ps1 -ClusterName $ClusterName

kubectl apply -k .\k8s

kubectl get pods -n observability-demo
kubectl get ingress -n observability-demo
