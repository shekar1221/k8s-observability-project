# Java Test Automation Module

This module adds Java-based test automation for the shopping observability project.

It includes:

- JUnit 5 unit tests
- Cucumber BDD feature files
- REST Assured API tests
- Optional Selenium browser smoke test
- Maven Surefire and Failsafe reports for CI artifacts

## Run Unit Tests

```powershell
cd test-automation
mvn test
```

## Run Real REST API Tests

Run these after the application is deployed.

For Rancher or any Kubernetes ingress URL:

```powershell
cd test-automation
mvn verify -DskipITs=false -DbaseUrl=http://shop.observability.local
```

For port-forward:

```powershell
kubectl port-forward svc/frontend 8080:8080 -n observability-demo
cd test-automation
mvn verify -DskipITs=false -DbaseUrl=http://localhost:8080
```

## Run Selenium Smoke Test

```powershell
cd test-automation
mvn verify -DskipITs=false -DrunSelenium=true -DbaseUrl=http://shop.observability.local
```

## Reports

JUnit reports:

```text
target/surefire-reports/
```

Cucumber and integration reports:

```text
target/failsafe-reports/
target/cucumber-reports/
```
