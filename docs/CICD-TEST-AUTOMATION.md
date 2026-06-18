# CI/CD, Trivy Scanning, and Java Test Automation

This project now includes a fuller CI/CD pipeline with DevSecOps scanning and Java-based automation tests.

Workflow file:

```text
.github/workflows/ci-cd.yml
```

Java test module:

```text
test-automation/
```

## Updated CI/CD Flow

```text
validate
  |
  v
java-tests
  |
  v
security-scan
  |
  v
image-scan
  |
  v
build and push images
  |
  v
optional e2e-tests by manual workflow_dispatch
```

## What Each Job Does

### validate

Checks the basic project health:

```text
kubectl kustomize k8s
python -m py_compile
```

### java-tests

Runs Java JUnit tests from:

```text
test-automation/
```

Command used in CI:

```bash
mvn -f test-automation/pom.xml test
```

Reports are uploaded from:

```text
test-automation/target/surefire-reports/
```

### security-scan

Runs repository and IaC security checks:

- kubeconform for Kubernetes schema validation
- Trivy filesystem scan for vulnerabilities, secrets, and misconfigurations
- Checkov for Kubernetes, Dockerfile, and GitHub Actions IaC checks
- Gitleaks for hardcoded secrets
- Hadolint for Dockerfile linting
- Bandit for Python SAST
- pip-audit for Python dependency vulnerabilities

### image-scan

Builds each Docker image locally in CI and scans it with Trivy before publishing.

Images scanned:

- `orders-api`
- `shopping-frontend`
- `user-api`
- `cart-api`
- `payment-api`
- `shipping-api`

Trivy blocks the build on `HIGH` and `CRITICAL` vulnerabilities:

```yaml
severity: HIGH,CRITICAL
exit-code: 1
```

### build

Builds and pushes images to GitHub Container Registry on `main` branch pushes:

```text
ghcr.io/<owner>/<image>:<git-sha>
ghcr.io/<owner>/<image>:latest
```

### e2e-tests

This job is optional and runs only from manual GitHub Actions dispatch.

Why optional?

```text
Real API and Selenium tests need a live deployed environment. In production teams, these usually run after deployment to a dev/QA environment, not on every pull request.
```

Manual inputs:

```text
run_e2e: true
base_url: http://shop.observability.local
```

Command used:

```bash
mvn -f test-automation/pom.xml verify -DskipITs=false -DrunSelenium=true -DbaseUrl=<base_url>
```

## Java Test Automation Design

### JUnit

Used for fast unit tests.

Example:

```text
test-automation/src/test/java/com/example/observability/api/LatencyBudgetTest.java
```

What it validates:

```text
Latency classification logic: OK, WARNING, CRITICAL.
```

### Cucumber

Used for BDD-style API scenarios.

Feature file:

```text
test-automation/src/test/resources/features/observability_api.feature
```

Example scenario:

```gherkin
Scenario: Frontend health endpoint is available
  Given the shopping frontend API is available
  When I call "/healthz"
  Then the response status should be 200
  And the response should contain "frontend"
```

### REST Assured

Used inside Cucumber step definitions to call real REST APIs.

Step file:

```text
test-automation/src/test/java/com/example/observability/steps/ApiStepDefinitions.java
```

REST API tests call:

- `/healthz`
- `/metrics`
- `/home`

### Selenium

Used for a simple browser smoke test.

Test file:

```text
test-automation/src/test/java/com/example/observability/ui/ShoppingHomeSeleniumIT.java
```

It is disabled by default and runs only when:

```text
-DrunSelenium=true
```

## Real-Time REST API Integration Steps

Use this flow in real projects.

### Step 1: Deploy Application

Deploy to a real environment such as:

- Rancher-managed RKE2 cluster
- OpenShift
- EKS
- AKS
- GKE
- Tanzu

Example URL:

```text
http://shop.observability.company.internal
```

### Step 2: Confirm API Manually

```powershell
curl.exe http://shop.observability.company.internal/healthz
curl.exe http://shop.observability.company.internal/home
curl.exe http://shop.observability.company.internal/metrics
```

### Step 3: Run Java REST API Tests

```powershell
cd test-automation
mvn verify -DskipITs=false -DbaseUrl=http://shop.observability.company.internal
```

### Step 4: Run from GitHub Actions

Go to:

```text
GitHub -> Actions -> shopping-platform-ci-cd -> Run workflow
```

Set:

```text
run_e2e = true
base_url = http://shop.observability.company.internal
```

### Step 5: Review Reports

Download artifacts:

```text
java-junit-reports
java-e2e-reports
```

### Step 6: Connect Test Results to Observability

When a test fails or is slow, check:

```powershell
kubectl get pods -n observability-demo
kubectl logs deploy/frontend -n observability-demo --tail=100
```

Prometheus:

```promql
histogram_quantile(0.95, sum(rate(frontend_request_latency_seconds_bucket[5m])) by (le, endpoint))
```

Loki:

```logql
{app="frontend"} |= "error"
```

Jaeger:

```text
Service: frontend
Sort by longest duration
Open the slow trace
```

## Interview Explanation

Use this:

```text
I added a CI/CD pipeline that validates Kubernetes manifests, runs Python syntax checks, runs Java JUnit tests, performs repository and IaC security scans, builds every container image, scans each image with Trivy, and only then pushes images to the registry. I also added an optional real-time E2E stage using Cucumber, REST Assured, and Selenium. The E2E stage is manually triggered with a base URL because it needs a live deployed environment, such as a Rancher-managed Kubernetes ingress URL.
```

## Common Interview Questions

### Why use Trivy in CI?

Trivy catches vulnerable packages, secrets, and misconfigurations before images are published or deployed.

### Why scan Docker images separately?

Filesystem scanning checks source code and IaC, while image scanning checks the final container filesystem, OS packages, and installed dependencies.

### Why use JUnit?

JUnit is used for fast Java unit tests that should run on every commit.

### Why use Cucumber?

Cucumber expresses business-readable API scenarios in Gherkin, which is useful when QA, developers, and business teams review the same behavior.

### Why use REST Assured?

REST Assured is a Java library commonly used for REST API automation. It makes status code, body, and header assertions simple.

### Why make Selenium optional?

Browser tests need a real deployed frontend and can be slower or flaky. They are useful after deployment to dev/QA but usually not required for every pull request.

### How do you integrate REST API tests in real time?

Deploy the application to a reachable environment, pass the environment base URL into the test job, run API tests against real endpoints, publish test reports, and use observability tools to investigate failures.
