param(
  [string]$Namespace = "observability-demo",
  [string]$IngressNamespace = "ingress-nginx",
  [int]$TimeoutSeconds = 180,
  [string]$IngressUrl = "http://localhost:8080",
  [switch]$NoWait,
  [switch]$TestIngress,
  [switch]$ShowLogs
)

$ErrorActionPreference = "Stop"
$script:HasFailures = $false

function Write-Section {
  param([string]$Title)
  Write-Host ""
  Write-Host "== $Title ==" -ForegroundColor Cyan
}

function Write-Ok {
  param([string]$Message)
  Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Warn {
  param([string]$Message)
  Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Fail {
  param([string]$Message)
  $script:HasFailures = $true
  Write-Host "[FAIL] $Message" -ForegroundColor Red
}

function Test-KubectlObject {
  param(
    [string[]]$Arguments,
    [string]$FailureMessage
  )

  & kubectl @Arguments *> $null
  if ($LASTEXITCODE -ne 0) {
    Write-Fail $FailureMessage
    return $false
  }

  return $true
}

function Get-DesiredReplicas {
  param($Deployment)

  if ($null -eq $Deployment.spec.replicas) {
    return 1
  }

  return [int]$Deployment.spec.replicas
}

function Get-Number {
  param($Value)

  if ($null -eq $Value) {
    return 0
  }

  return [int]$Value
}

function Get-PodProblem {
  param($Pod)

  $phase = [string]$Pod.status.phase
  $containerStatuses = @()
  if ($Pod.status.containerStatuses) {
    $containerStatuses = @($Pod.status.containerStatuses)
  }

  $waitingReasons = @(
    $containerStatuses |
      Where-Object { $_.state.waiting } |
      ForEach-Object { "$($_.name):$($_.state.waiting.reason)" }
  )

  $notReadyContainers = @(
    $containerStatuses |
      Where-Object { -not $_.ready } |
      ForEach-Object { $_.name }
  )

  if ($phase -ne "Running" -and $phase -ne "Succeeded") {
    if ($waitingReasons.Count -gt 0) {
      return "$phase ($($waitingReasons -join ', '))"
    }
    return $phase
  }

  if ($phase -eq "Running" -and $notReadyContainers.Count -gt 0) {
    if ($waitingReasons.Count -gt 0) {
      return "containers not ready ($($waitingReasons -join ', '))"
    }
    return "containers not ready ($($notReadyContainers -join ', '))"
  }

  return $null
}

if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
  Write-Fail "kubectl is not available in PATH"
  exit 1
}

Write-Section "Context"
$context = & kubectl config current-context
if ($LASTEXITCODE -ne 0) {
  Write-Fail "Could not read current kubectl context"
  exit 1
}
Write-Host "Current context: $context"

if (-not (Test-KubectlObject -Arguments @("get", "namespace", $Namespace) -FailureMessage "Namespace '$Namespace' was not found")) {
  exit 1
}

Write-Section "Cluster"
& kubectl get nodes -o wide
if (-not $NoWait) {
  & kubectl wait node --all --for=condition=Ready --timeout="${TimeoutSeconds}s"
  if ($LASTEXITCODE -eq 0) {
    Write-Ok "All nodes are Ready"
  } else {
    Write-Fail "One or more nodes are not Ready"
  }
}

Write-Section "Ingress Controller"
if (Test-KubectlObject -Arguments @("get", "namespace", $IngressNamespace) -FailureMessage "Namespace '$IngressNamespace' was not found") {
  & kubectl get pods -n $IngressNamespace -l app.kubernetes.io/component=controller -o wide
  if (-not $NoWait) {
    & kubectl wait -n $IngressNamespace --for=condition=ready pod --selector=app.kubernetes.io/component=controller --timeout="${TimeoutSeconds}s"
    if ($LASTEXITCODE -eq 0) {
      Write-Ok "Ingress controller is Ready"
    } else {
      Write-Fail "Ingress controller is not Ready"
    }
  }
}

Write-Section "Application Workloads"
& kubectl get deploy,daemonset,statefulset -n $Namespace -o wide

if (-not $NoWait) {
  & kubectl wait -n $Namespace --for=condition=Available deployment --all --timeout="${TimeoutSeconds}s"
  if ($LASTEXITCODE -eq 0) {
    Write-Ok "All deployments are Available"
  } else {
    Write-Fail "One or more deployments are not Available"
  }
}

$deploymentsJson = & kubectl get deployments -n $Namespace -o json
$deployments = ($deploymentsJson | ConvertFrom-Json).items
foreach ($deployment in @($deployments)) {
  $desired = Get-DesiredReplicas $deployment
  $ready = Get-Number $deployment.status.readyReplicas
  $available = Get-Number $deployment.status.availableReplicas
  $name = [string]$deployment.metadata.name

  if ($ready -eq $desired -and $available -eq $desired) {
    Write-Ok "deployment/$name ready $ready/$desired"
  } else {
    Write-Fail "deployment/$name ready $ready/$desired, available $available/$desired"
  }
}

$daemonsetsJson = & kubectl get daemonsets -n $Namespace -o json
$daemonsets = ($daemonsetsJson | ConvertFrom-Json).items
foreach ($daemonset in @($daemonsets)) {
  $desired = Get-Number $daemonset.status.desiredNumberScheduled
  $ready = Get-Number $daemonset.status.numberReady
  $available = Get-Number $daemonset.status.numberAvailable
  $name = [string]$daemonset.metadata.name

  if ($ready -eq $desired -and $available -eq $desired) {
    Write-Ok "daemonset/$name ready $ready/$desired"
  } else {
    Write-Fail "daemonset/$name ready $ready/$desired, available $available/$desired"
  }
}

Write-Section "Pods"
& kubectl get pods -n $Namespace -o wide

$podsJson = & kubectl get pods -n $Namespace -o json
$pods = ($podsJson | ConvertFrom-Json).items
$badPods = @(
  foreach ($pod in @($pods)) {
    $problem = Get-PodProblem $pod
    if ($problem) {
      [PSCustomObject]@{
        Name = [string]$pod.metadata.name
        Problem = $problem
      }
    }
  }
)

if ($badPods.Count -eq 0) {
  Write-Ok "All pods are Running/Ready or Completed"
} else {
  Write-Fail "$($badPods.Count) pod(s) need attention"
  $badPods | Format-Table -AutoSize
}

Write-Section "Services And Ingress"
& kubectl get svc,ingress -n $Namespace -o wide

if ($TestIngress) {
  Write-Section "Ingress HTTP Checks"

  if (-not (Get-Command curl.exe -ErrorAction SilentlyContinue)) {
    Write-Warn "curl.exe was not found, skipping ingress HTTP checks"
  } else {
    $ingressJson = & kubectl get ingress -n $Namespace -o json
    $ingresses = ($ingressJson | ConvertFrom-Json).items
    $hosts = @(
      foreach ($ingress in @($ingresses)) {
        foreach ($rule in @($ingress.spec.rules)) {
          if ($rule.host) {
            [string]$rule.host
          }
        }
      }
    ) | Sort-Object -Unique

    foreach ($hostName in $hosts) {
      $statusCode = & curl.exe --silent --show-error --output NUL --write-out "%{http_code}" --header "Host: $hostName" $IngressUrl
      if ($LASTEXITCODE -eq 0 -and $statusCode -match "^[23]") {
        Write-Ok "$hostName -> HTTP $statusCode"
      } else {
        Write-Fail "$hostName -> HTTP $statusCode"
      }
    }
  }
}

if ($badPods.Count -gt 0) {
  Write-Section "Diagnostics"
  foreach ($badPod in $badPods) {
    Write-Host ""
    Write-Host "-- pod/$($badPod.Name): $($badPod.Problem) --" -ForegroundColor Yellow
    & kubectl describe pod $badPod.Name -n $Namespace

    if ($ShowLogs) {
      Write-Host ""
      Write-Host "-- recent logs for pod/$($badPod.Name) --" -ForegroundColor Yellow
      & kubectl logs $badPod.Name -n $Namespace --all-containers --tail=80
    }
  }
}

Write-Section "Result"
if ($script:HasFailures) {
  Write-Fail "Deployment check completed with issues"
  exit 1
}

Write-Ok "Deployment check passed"
