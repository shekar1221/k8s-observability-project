# GitHub Actions Deployment Guide

This guide explains how to deploy the 3-tier project using the GitHub Actions workflow in `cicd-3tier-develop.yaml`.

## 1. Add the workflow file

In your project repository, create this folder if it does not already exist:

```text
.github/workflows/
```

Copy the workflow file into that folder:

```text
.github/workflows/cicd-3tier-develop.yaml
```

The workflow is configured to run for these branches:

```yaml
branches:
  - main
  - develop
```

## 2. Required project files

The workflow expects these Kubernetes manifest files at the root of your repository:

```text
cart.yaml
frontend.yaml
payment.yaml
shipping.yaml
user.yaml
```

It also expects each service to have its own Docker build folder:

```text
cart/
frontend/
payment/
shipping/
user/
```

Each folder should contain a `Dockerfile`.

Example:

```text
cart/Dockerfile
frontend/Dockerfile
payment/Dockerfile
shipping/Dockerfile
user/Dockerfile
```

If your repository uses a different folder structure, update this section in the workflow:

```yaml
with:
  context: ./${{ matrix.service }}
```

## 3. Add GitHub repository secrets

Go to your GitHub repository:

```text
Settings > Secrets and variables > Actions > New repository secret
```

Add these secrets:

```text
KUBE_CONFIG_DEVELOP
KUBE_CONFIG_PRODUCTION
```

`KUBE_CONFIG_DEVELOP` should contain the kubeconfig for your develop Kubernetes cluster or namespace.

`KUBE_CONFIG_PRODUCTION` should contain the kubeconfig for your production Kubernetes cluster or namespace.

You can get your kubeconfig from your Kubernetes environment with:

```bash
kubectl config view --raw
```

Copy the full output and paste it into the GitHub secret value.

## 4. Deployment behavior

When you push to `develop`, GitHub Actions will:

1. Validate `cart.yaml`, `frontend.yaml`, `payment.yaml`, `shipping.yaml`, and `user.yaml`.
2. Build Docker images for all services.
3. Push images to GitHub Container Registry.
4. Deploy the manifests to the `develop` GitHub environment.

When you push to `main`, GitHub Actions will:

1. Validate the Kubernetes manifests.
2. Build Docker images for all services.
3. Push images to GitHub Container Registry.
4. Deploy the manifests to the `production` GitHub environment.

Pull requests to `main` or `develop` only run validation. They do not deploy.

## 5. Trigger deployment

To deploy to the develop environment:

```bash
git checkout develop
git add .
git commit -m "Add CI/CD deployment workflow"
git push origin develop
```

To deploy to production:

```bash
git checkout main
git merge develop
git push origin main
```

## 6. GitHub Container Registry permissions

The workflow pushes images to GitHub Container Registry using:

```text
ghcr.io
```

The workflow already includes this permission:

```yaml
permissions:
  contents: read
  packages: write
```

No extra Docker registry secret is needed when using GitHub Container Registry with `GITHUB_TOKEN`.

## 7. Important image note

The workflow builds and pushes images, but your Kubernetes manifests must reference deployable image names.

For example:

```yaml
image: ghcr.io/OWNER/REPOSITORY/frontend:develop
```

Replace `OWNER/REPOSITORY` with your actual GitHub repository path.

Example:

```yaml
image: ghcr.io/my-org/three-tier-app/frontend:develop
```

Do this for all services:

```text
cart
frontend
payment
shipping
user
```

## 8. Verify deployment

After the GitHub Action finishes, check your Kubernetes resources:

```bash
kubectl get pods -n three-tier
kubectl get services -n three-tier
kubectl get deployments -n three-tier
```

If a deployment fails, check logs:

```bash
kubectl logs -n three-tier deployment/frontend
kubectl describe pod -n three-tier <pod-name>
```

## 9. Manual run

The workflow also supports manual deployment from GitHub:

```text
Actions > 3-tier CI/CD > Run workflow
```

Choose either the `develop` or `main` branch.

