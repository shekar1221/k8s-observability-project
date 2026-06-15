# Upgrade the Shopping Cart App with Argo CD

This guide shows how to upgrade the application from `orders-api:local` / `APP_VERSION=v1` to `orders-api:v2` / `APP_VERSION=v2` using Argo CD.

## What Changes in v2

The `v2` overlay changes only the application Deployment:

```text
k8s-upgrades/v2/
```

It patches:

```yaml
image: orders-api:v2
APP_VERSION: v2
pod label version: v2
```

The `/` endpoint returns the app version:

```json
{
  "service": "orders-api",
  "version": "v2"
}
```

## Important for Kind

Argo CD deploys YAML from Git, but it does not build local Docker images.

Before syncing the v2 Argo CD app, build and load the v2 image into Kind:

```powershell
cd D:\k8s-observability-project
docker build -t orders-api:v2 .\app
kind load docker-image orders-api:v2 --name observability
```

If you skip this, pods may fail with:

```text
ImagePullBackOff
```

## Step 1: Push the v2 Overlay to Git

Commit and push the new overlay and Argo CD app file:

```powershell
git add app app.py k8s-upgrades argocd
git commit -m "Add Argo CD v2 upgrade overlay"
git push
```

If your shell says `app.py` is not found, use:

```powershell
git add app k8s-upgrades argocd
git commit -m "Add Argo CD v2 upgrade overlay"
git push
```

## Step 2: Replace Repo URL

Edit:

```text
argocd/applications/observability-app-v2.yaml
```

Replace:

```text
REPLACE_WITH_YOUR_GIT_REPO_URL
```

with:

```text
https://github.com/shekar1221/k8s-observability-project.git
```

Commit and push if needed:

```powershell
git add argocd/applications/observability-app-v2.yaml
git commit -m "Configure Argo CD v2 repo URL"
git push
```

## Step 3: Apply the v2 Argo CD Application

This uses the same Argo CD Application name, `observability-stack`, but changes the source path to:

```text
k8s-upgrades/v2
```

Apply:

```powershell
kubectl apply -f .\argocd\applications\observability-app-v2.yaml
```

Refresh Argo CD:

```powershell
kubectl annotate application observability-stack -n argocd argocd.argoproj.io/refresh=hard --overwrite
```

If auto-sync does not run immediately, sync from the UI or CLI:

```powershell
argocd app sync observability-stack
```

## Step 4: Watch the Rollout

```powershell
kubectl rollout status deployment/orders-api -n observability-demo
kubectl get pods -n observability-demo -l app=orders-api --show-labels
```

You should see:

```text
version=v2
```

## Step 5: Verify the Upgrade

Port-forward the app:

```powershell
kubectl port-forward svc/orders-api 8080:8080 -n observability-demo
```

Test:

```powershell
curl http://localhost:8080/
curl http://localhost:8080/products
```

Expected from `/`:

```json
"version": "v2"
```

Check image:

```powershell
kubectl get deployment orders-api -n observability-demo -o jsonpath="{.spec.template.spec.containers[0].image}"
```

Expected:

```text
orders-api:v2
```

## Step 6: Roll Back to v1

Apply the original Argo CD app:

```powershell
kubectl apply -f .\argocd\applications\observability-app.yaml
kubectl annotate application observability-stack -n argocd argocd.argoproj.io/refresh=hard --overwrite
```

Sync:

```powershell
argocd app sync observability-stack
```

Then check:

```powershell
kubectl rollout status deployment/orders-api -n observability-demo
kubectl get deployment orders-api -n observability-demo -o jsonpath="{.spec.template.spec.containers[0].image}"
```

Expected:

```text
orders-api:local
```

## Interview Explanation

Use this:

Argo CD is used to upgrade the shopping cart application through GitOps. The base app points to the `k8s/` path. For the upgrade, I created a Kustomize overlay at `k8s-upgrades/v2` that changes the app image to `orders-api:v2`, adds an `APP_VERSION=v2` environment variable, and labels pods with `version=v2`. After pushing the change to Git, Argo CD detects the desired state change and syncs it to the cluster. In Kind, the local image must be built and loaded into the Kind node before Argo CD syncs the deployment.

## Troubleshooting Upgrade Problems

### ImagePullBackOff

Cause:

```text
orders-api:v2 was not loaded into Kind.
```

Fix:

```powershell
docker build -t orders-api:v2 .\app
kind load docker-image orders-api:v2 --name observability
kubectl rollout restart deployment/orders-api -n observability-demo
```

### Argo CD Still Shows Old Version

Check app source path:

```powershell
kubectl describe application observability-stack -n argocd
```

Look for:

```text
Path: k8s-upgrades/v2
```

Refresh:

```powershell
kubectl annotate application observability-stack -n argocd argocd.argoproj.io/refresh=hard --overwrite
```

### Pods Running But Service Not Working

Check endpoints:

```powershell
kubectl get endpoints orders-api -n observability-demo
kubectl describe svc orders-api -n observability-demo
```

The Service selector should be:

```text
app=orders-api
```
