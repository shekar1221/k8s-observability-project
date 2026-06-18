# CI Security Scanning

This project includes security scanning in GitHub Actions.

Workflow:

```text
.github/workflows/ci-cd.yml
```

## What Runs in CI

| Tool | Purpose | What it catches |
|---|---|---|
| kubeconform | Kubernetes schema validation | Invalid Kubernetes YAML fields and API schema issues |
| Trivy | Vulnerability, secret, and misconfiguration scan | Vulnerable packages, leaked secrets, risky Docker/Kubernetes config |
| Checkov | Infrastructure as Code scan | Kubernetes, Dockerfile, and GitHub Actions misconfigurations |
| Gitleaks | Secret scanning | Hardcoded passwords, tokens, API keys, private keys |
| Hadolint | Dockerfile linting | Dockerfile best-practice issues |
| Bandit | Python SAST | Risky Python code patterns |
| pip-audit | Python dependency audit | Known CVEs in Python packages |
| Trivy image scan | Container image vulnerability scan | Vulnerabilities in final built images |

## CI Flow

```text
validate
  |
  v
security-scan
  |
  v
build and push images
```

The image build runs only after validation and security scanning pass.

The workflow also builds every service image in the `image-scan` job and scans it with Trivy before publishing images.

## Why These Tools Are Useful

### kubeconform

Kubernetes accepts YAML only if the structure matches the Kubernetes API. `kubeconform` catches wrong fields before deployment.

Example issue:

```text
Wrong indentation or invalid Deployment field.
```

### Trivy

Trivy scans the repository for:

- OS package vulnerabilities
- Python dependency vulnerabilities
- Kubernetes misconfigurations
- Dockerfile issues
- Secrets

In this workflow, Trivy fails CI for `HIGH` and `CRITICAL` findings.

### Trivy Image Scanning

Filesystem scanning checks source code and YAML. Image scanning checks the final container image after Docker build.

The pipeline scans:

- `orders-api`
- `shopping-frontend`
- `user-api`
- `cart-api`
- `payment-api`
- `shipping-api`

This is important because an image can contain vulnerable OS packages or installed dependencies even when the source code looks clean.

### Checkov

Checkov is useful for Kubernetes and CI/CD misconfiguration checks.

Example issues:

- Containers running as root
- Missing resource limits
- Missing readiness/liveness probes
- Risky GitHub Actions permissions

### Gitleaks

Gitleaks detects hardcoded secrets.

Example issue:

```text
AWS_SECRET_ACCESS_KEY=...
GITHUB_TOKEN=...
private_key=...
```

### Hadolint

Hadolint checks Dockerfile quality.

Example issues:

- Using latest tags
- Not pinning packages
- Bad shell usage in `RUN`

### Bandit

Bandit scans Python code for common security issues.

Example issues:

- Hardcoded passwords
- Unsafe shell commands
- Weak cryptography
- Unsafe deserialization

### pip-audit

`pip-audit` checks Python dependencies against known vulnerability databases.

Example:

```text
Flask or requests version has a known CVE.
```

## Local Commands

Run these from the project root.

### Validate Kubernetes YAML

```powershell
kubectl kustomize .\k8s > rendered.yaml
```

If you have Docker:

```powershell
docker run --rm -v ${PWD}:/work -w /work ghcr.io/yannh/kubeconform:v0.6.7 -strict -summary -ignore-missing-schemas rendered.yaml
```

### Run Trivy

```powershell
docker run --rm -v ${PWD}:/work -w /work aquasec/trivy:0.69.3 fs --scanners vuln,secret,misconfig --severity HIGH,CRITICAL --ignore-unfixed .
```

### Run Checkov

```powershell
pip install checkov
checkov -d . --framework kubernetes,github_actions,dockerfile
```

### Run Gitleaks

```powershell
docker run --rm -v ${PWD}:/path zricethezav/gitleaks:v8.28.0 detect --source=/path --verbose
```

### Run Hadolint

```powershell
docker run --rm -v ${PWD}:/work hadolint/hadolint:2.12.0-debian /work/app/Dockerfile /work/services/frontend/Dockerfile /work/services/user-api/Dockerfile /work/services/cart-api/Dockerfile /work/services/payment-api/Dockerfile /work/services/shipping-api/Dockerfile
```

### Run Bandit

```powershell
pip install bandit
bandit -r app services interview-code -ll
```

### Run pip-audit

```powershell
pip install pip-audit
pip-audit -r app\requirements.txt
pip-audit -r services\common\requirements.txt
```

## How to Explain in Interview

Use this:

```text
I added DevSecOps checks into the CI pipeline. The workflow first validates Kubernetes manifests and Python syntax. Then it runs Java unit tests, security scans, and image scans. The security stage uses kubeconform, Trivy filesystem scanning, Checkov, Gitleaks, Hadolint, Bandit, and pip-audit. The image-scan stage builds every service image and scans it with Trivy before publishing. Trivy, Gitleaks, Hadolint, Bandit, and pip-audit can block the build. Checkov is currently advisory so I can review Kubernetes hardening findings without stopping every learning build.
```

## Common Interview Questions

### Why scan before building images?

Scanning before build catches issues early and avoids publishing insecure images.

### What is the difference between SAST and dependency scanning?

SAST scans source code patterns. Dependency scanning checks third-party packages for known CVEs.

### What is IaC scanning?

IaC scanning checks infrastructure files like Kubernetes YAML, Terraform, Dockerfiles, and GitHub Actions for misconfigurations.

### What should you do if CI finds a critical vulnerability?

Identify the affected package or image, upgrade to a fixed version, rebuild the image, rerun CI, and redeploy through Argo CD.

### What should you do if secret scanning finds a leaked secret?

Immediately revoke or rotate the secret, remove it from code, purge it from history if needed, and use a secret manager or Kubernetes Secret workflow.
