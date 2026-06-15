# Argo CD GitOps Setup for This Observability Project

This folder adds Argo CD support for the same Kubernetes observability project.

Use Argo CD to:

- deploy the observability stack from Git
- detect drift when someone changes Kubernetes resources manually
- sync the desired YAML back into the cluster
- practice troubleshooting broken overlays from `troubleshooting-labs/`

## Important Note

Argo CD deploys Kubernetes YAML from a Git repository. It does not build Docker images for this project.

For Kind, still build and load the local image first:

```powershell
docker build -t orders-api:local .\app
kind load docker-image orders-api:local --name observability
```

Then Argo CD can deploy the Kubernetes manifests.

## Step 1: Push This Project to Git

Create a Git repo from this folder and push it to GitHub/GitLab/Bitbucket.

Example:

```powershell
git init
git add .
git commit -m "Add observability project with troubleshooting labs"
git branch -M main
git remote add origin https://github.com/YOUR_USER/k8s-observability-project-codex.git
git push -u origin main
```

Replace the repo URL in the files under:

```text
argocd/applications/
argocd/error-lab-applications/
```

Find:

```text
REPLACE_WITH_YOUR_GIT_REPO_URL
```

Replace it with your actual Git repo URL.

## Step 2: Install Argo CD

Create the namespace:

```powershell
kubectl create namespace argocd
```

Install Argo CD:

```powershell
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

Wait for pods:

```powershell
kubectl wait --for=condition=available deployment/argocd-server -n argocd --timeout=300s
kubectl get pods -n argocd
```

## Step 3: Open Argo CD UI

Port-forward:

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

Get the initial password:

```powershell
kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath="{.data.password}"
```

Decode it:

```powershell
[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String((kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath="{.data.password}")))
```

## Step 4: Deploy the Working Observability Stack

Edit:

```text
argocd/applications/observability-app.yaml
```

Replace:

```text
REPLACE_WITH_YOUR_GIT_REPO_URL
```

Apply:

```powershell
kubectl apply -f .\argocd\applications\observability-app.yaml
```

Check:

```powershell
kubectl get applications -n argocd
kubectl get pods -n observability-demo
```

In Argo CD UI, the app should show:

```text
Healthy / Synced
```

## Step 5: Fix Manual Drift Using Argo CD

Example: manually break the service selector:

```powershell
kubectl patch svc orders-api -n observability-demo --type merge -p '{\"spec\":{\"selector\":{\"app\":\"wrong-label\"}}}'
```

Check endpoints:

```powershell
kubectl get endpoints orders-api -n observability-demo
```

Expected:

```text
ENDPOINTS empty
```

Argo CD will show:

```text
OutOfSync
```

Fix using Argo CD:

```powershell
kubectl annotate application observability-stack -n argocd argocd.argoproj.io/refresh=hard --overwrite
```

Then in the UI click:

```text
SYNC
```

Or use CLI if installed:

```powershell
argocd app sync observability-stack
```

The service selector should return to:

```text
app: orders-api
```

## Step 6: Practice Error Labs Through Argo CD

Each file under `argocd/error-lab-applications/` points to a broken overlay in:

```text
troubleshooting-labs/
```

For example:

```powershell
kubectl apply -f .\argocd\error-lab-applications\lab-02-service-selector-503.yaml
```

Argo CD will deploy the broken desired state from Git.

To fix it, switch back to the working app:

```powershell
kubectl delete application observability-lab-02 -n argocd
kubectl apply -f .\argocd\applications\observability-app.yaml
```

Or commit the fix in Git and sync again.

## What Argo CD Can and Cannot Fix

Argo CD can fix:

- manual changes to YAML-managed resources
- wrong service selectors if Git has the correct selector
- wrong readiness probe paths if Git has the correct path
- wrong ConfigMap values if Git has the correct values
- deleted Kubernetes resources that still exist in Git

Argo CD cannot automatically fix:

- Docker image missing from Kind
- application code bugs inside the image
- syntax errors committed to Git
- cluster/Docker Desktop not running
- not enough CPU/memory

For local Kind image issues, rebuild and reload:

```powershell
docker build -t orders-api:local .\app
kind load docker-image orders-api:local --name observability
kubectl rollout restart deployment/orders-api -n observability-demo
```

## Useful Argo CD Commands

```powershell
kubectl get applications -n argocd
kubectl describe application observability-stack -n argocd
kubectl get events -n argocd --sort-by=.lastTimestamp
kubectl logs deploy/argocd-application-controller -n argocd
kubectl logs deploy/argocd-server -n argocd
```

If Argo CD says the repo is unreachable, check:

- repo URL is correct
- repo is public, or credentials are configured
- branch name is correct
- `path` points to a real folder

## Recommended Interview Explanation

Use this:

Argo CD is used as the GitOps controller. The desired Kubernetes manifests live in Git, and Argo CD continuously compares the live cluster state against that desired state. If someone manually changes a service selector, readiness probe, ConfigMap, or deployment value, Argo CD marks the app OutOfSync. We can sync the app to restore the Git-defined desired state. For application image problems in Kind, Argo CD still needs the image to exist in the local Kind node or in a reachable registry.
