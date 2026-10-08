# Netshoot Enterprise Usage Guide

## What Is Netshoot?

`netshoot` is a container image that contains many network troubleshooting tools.

It is useful when an application pod does not have tools like:

- `curl`
- `dig`
- `nslookup`
- `nc`
- `tcpdump`
- `ip`
- `traceroute`

In Kubernetes production support, `netshoot` is used as a temporary debugging pod to test DNS, service connectivity, ports, routing, and network policies from inside the cluster.

## Is Netshoot Enterprise Level?

Yes and no.

`netshoot` is enterprise-useful, but it is normally not deployed as a permanent enterprise application.

In enterprise or BFSI environments, it is used as a temporary troubleshooting tool by SRE, DevOps, platform, or Kubernetes support teams.

## Enterprise Practice

| Area | Recommended Practice |
|---|---|
| Image source | Use an approved image from an internal registry |
| Image tag | Avoid `latest`; use a fixed version or digest |
| Access | Allow only approved SRE/platform users through RBAC |
| Namespace | Use a controlled debug or support namespace |
| Lifetime | Delete the pod after troubleshooting |
| Security | Avoid privileged mode unless approved |
| Audit | Ensure Kubernetes audit logs capture usage |
| Network | NetworkPolicy may restrict where the pod can connect |
| Production use | Use only during incident/debugging windows |

## Lab Usage

In this lab, the base manifest creates a `netshoot` pod:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: netshoot
  namespace: troubleshooting-lab
  labels:
    app: netshoot
spec:
  containers:
    - name: netshoot
      image: nicolaka/netshoot:latest
      command: ["sleep", "3600"]
```

This keeps the pod running for 1 hour so you can enter it and test services.

## Login To Netshoot Pod

```bash
kubectl exec -it netshoot -n troubleshooting-lab -- bash
```

If `bash` is not available:

```bash
kubectl exec -it netshoot -n troubleshooting-lab -- sh
```

## Useful Commands Inside Netshoot

Check service DNS:

```bash
nslookup orders-api.troubleshooting-lab.svc.cluster.local
dig orders-api.troubleshooting-lab.svc.cluster.local
```

Check HTTP service:

```bash
curl -v http://orders-api.troubleshooting-lab.svc.cluster.local
```

Check TCP port:

```bash
nc -vz payments-db.troubleshooting-lab.svc.cluster.local 5432
```

Check route:

```bash
ip route
```

Check pod IP/interface:

```bash
ip addr
```

## Temporary Debug Pod Command

In many teams, instead of keeping a permanent pod, engineers create a temporary pod:

```bash
kubectl run netshoot-debug \
  --image=nicolaka/netshoot:v0.13 \
  -n troubleshooting-lab \
  --rm -it -- bash
```

This deletes the pod automatically when you exit.

## Enterprise-Style Command

In a strict enterprise environment, do not pull directly from a public registry in production. Use an approved internal registry:

```bash
kubectl run netshoot-debug \
  --image=internal-registry.example.com/platform/netshoot:v0.13 \
  -n support-tools \
  --rm -it -- bash
```

## Debug Existing Application Pod

If the application image does not have shell or network tools, use ephemeral debugging:

```bash
kubectl debug -it deploy/orders-api \
  -n troubleshooting-lab \
  --image=nicolaka/netshoot:v0.13 \
  --target=app
```

Enterprise version:

```bash
kubectl debug -it deploy/orders-api \
  -n payments \
  --image=internal-registry.example.com/platform/netshoot:v0.13 \
  --target=app
```

## Real-Time Issue Example

Issue:

```text
Frontend application cannot connect to orders-api service.
```

Troubleshooting:

```bash
kubectl get svc,endpoints -n troubleshooting-lab
kubectl exec -it netshoot -n troubleshooting-lab -- bash
```

Inside netshoot:

```bash
nslookup orders-api.troubleshooting-lab.svc.cluster.local
curl -v http://orders-api.troubleshooting-lab.svc.cluster.local
```

Possible findings:

| Finding | Meaning | Next Check |
|---|---|---|
| DNS fails | CoreDNS or wrong service name | Check CoreDNS and service name |
| DNS works but curl times out | NetworkPolicy or backend issue | Check NetworkPolicy and endpoints |
| DNS works but connection refused | Wrong targetPort or app not listening | Check service targetPort and pod logs |
| Endpoint is empty | Service selector mismatch | Compare service selector and pod labels |

## Interview Answer

```text
Netshoot is a common troubleshooting image used by SRE and platform teams. In enterprise production, we do not use arbitrary public images directly. We use internally approved and scanned images, controlled RBAC, temporary debug pods, and audit logging. I use netshoot to validate DNS, service endpoints, TCP ports, HTTP response, routing, and network policy behavior from inside the Kubernetes cluster.
```

## Important Note

Kubernetes service DNS names like this:

```text
orders-api.troubleshooting-lab.svc.cluster.local
```

work from inside the Kubernetes cluster.

They usually do not resolve from Windows PowerShell, Git Bash, or your laptop terminal unless you configure special cluster DNS forwarding.

For service DNS testing, always run the command from a pod such as `netshoot`.

