'''
$ kubectl describe pod orders-api-85cb9c696b-dncjm -n observability-demo  |tail

Events:
  Type     Reason     Age                   From               Message
  ----     ------     ----                  ----               -------
  Normal   Scheduled  30m                   default-scheduler  Successfully assigned observability-demo/orders-api-85cb9c696b-dncjm to observability-control-plane
  Warning  Failed     22m (x5 over 29m)     kubelet            spec.containers{orders-api}: Error: ErrImagePull
  Normal   Pulling    19m (x6 over 30m)     kubelet            spec.containers{orders-api}: Pulling image "orders-api:local"
  Warning  Failed     8m47s (x68 over 29m)  kubelet            spec.containers{orders-api}: Error: ImagePullBackOff
  Normal   BackOff    4m45s (x87 over 29m)  kubelet            spec.containers{orders-api}: Back-off pulling image "orders-api:local"
  Warning  Failed     3m51s (x9 over 29m)   kubelet            spec.containers{orders-api}: Failed to pull image "orders-api:local": failed to pull and unpack image "docker.io/library/orders-api:local": failed to resolve reference "docker.io/library/orders-api:local": pull access denied, repository does not exist or may require authorization: server message: insufficient_scope: authorization failed
  
 '''
'''
 PS D:\k8s-observability-project> kind load docker-image orders-api:local --name observability
Image: "orders-api:local" with ID "sha256:a7abc9516bcfe3543730bbd37d14c3837136b3c00ac4d85e4819f43e1723799f" not yet present on node "observability-control-plane", loading...
PS D:\k8s-observability-project> kubectl rollout restart deployment/orders-api -n observability-demo
deployment.apps/orders-api restarted
PS D:\k8s-observability-project> kubectl get pods -n observability-demo -l app=orders-api
NAME                          READY   STATUS        RESTARTS   AGE
orders-api-664665b5d9-ddkmx   1/1     Running       0          7s
orders-api-664665b5d9-wzsgb   1/1     Running       0          14s
orders-api-85cb9c696b-dncjm   1/1     Terminating   0          33m
orders-api-85cb9c696b-pdb87   1/1     Terminating   0          33m
PS D:\k8s-observability-project> kubectl wait --for=condition=available deployment/orders-api -n observability-demo --timeout=180s
deployment.apps/orders-api condition met
PS D:\k8s-observability-project> kubectl get pods -n observability-demo -l app=orders-api
NAME                          READY   STATUS        RESTARTS   AGE
orders-api-664665b5d9-ddkmx   1/1     Running       0          28s
orders-api-664665b5d9-wzsgb   1/1     Running       0          35s
orders-api-85cb9c696b-dncjm   1/1     Terminating   0          33m
orders-api-85cb9c696b-pdb87   1/1     Terminating   0          33m
PS D:\k8s-observability-project>
PS D:\k8s-observability-project> kubectl get endpoints orders-api -n observability-demo
Warning: v1 Endpoints is deprecated in v1.33+; use discovery.k8s.io/v1 EndpointSlice
NAME         ENDPOINTS                           AGE
orders-api   10.244.0.23:8080,10.244.0.24:8080   34m
PS D:\k8s-observability-project>

**** 503 error -- selector mismatch --- endpoints showing empty ***

$ kubectl describe svc orders-api -n observability-demo
Name:                     orders-api
Namespace:                observability-demo
Labels:                   <none>
Annotations:              argocd.argoproj.io/tracking-id: observability-lab-02:/Service:observability-demo/orders-api
Selector:                 app=orders-api-wrong-label
Type:                     ClusterIP
IP Family Policy:         SingleStack
IP Families:              IPv4
IP:                       10.96.91.125
IPs:                      10.96.91.125
Port:                     http  8080/TCP
TargetPort:               8080/TCP
Endpoints:
Session Affinity:         None
Internal Traffic Policy:  Cluster
Events:                   <none>

shekk@Shekkar MINGW64 ~ (main)
$ kubectl get endpoints orders-api -n observability-demo
Warning: v1 Endpoints is deprecated in v1.33+; use discovery.k8s.io/v1 EndpointSlice
NAME         ENDPOINTS   AGE
orders-api   <none>      57m
'''

****FIX ***
$ kubectl describe application observability-lab-02 -n argocd  |grep -i outofsync
  Normal  ResourceUpdated     26m    argocd-application-controller  Updated sync status:  -> OutOfSync
  Normal  ResourceUpdated     26m    argocd-application-controller  Updated sync status: OutOfSync -> Synced
  Normal  ResourceUpdated     26m    argocd-application-controller  Updated sync status: Synced -> OutOfSync
  Normal  ResourceUpdated     24m    argocd-application-controller  Updated sync status: OutOfSync -> Synced
  Normal  ResourceUpdated     21m    argocd-application-controller  Updated sync status: Synced -> OutOfSync
  Normal  ResourceUpdated     16m    argocd-application-controller  Updated sync status: OutOfSync -> Synced
  Normal  ResourceUpdated     11m    argocd-application-controller  Updated sync status: Synced -> OutOfSync
  Normal  ResourceUpdated     11m    argocd-application-controller  Updated sync status: OutOfSync -> Synced
  Normal  ResourceUpdated     6m48s  argocd-application-controller  Updated sync status: Synced -> OutOfSync
  Normal  ResourceUpdated     6m42s  argocd-application-controller  Updated sync status: OutOfSync -> Synced
  Normal  ResourceUpdated     106s   argocd-application-controller  Updated sync status: Synced -> OutOfSync
  Normal  ResourceUpdated     100s   argocd-application-controller  Updated sync status: OutOfSync -> Synced

shekk@Shekkar MINGW64 ~ (main)
$ kubectl get applications -n argocd
NAME                   SYNC STATUS   HEALTH STATUS
observability-lab-02   Synced        Healthy
observability-stack    OutOfSync     Healthy

***if we run normally argocd goes outofsync **
$ kubectl patch svc orders-api -n observability-demo --type merge -p '{"spec":{"selector":{"app":"orders-api"}}}'
service/orders-api patched
$ kubectl get applications -n argocd
NAME                   SYNC STATUS   HEALTH STATUS
observability-lab-02   OutOfSync     Healthy
observability-stack    OutOfSync     Healthy



##### use argocd as well######

shekk@Shekkar MINGW64 ~ (main)
$ kubectl delete application observability-lab-02 -n argocd
application.argoproj.io "observability-lab-02" deleted from argocd namespace

shekk@Shekkar MINGW64 ~ (main)
$ kubectl get applications -n argocd
NAME                  SYNC STATUS   HEALTH STATUS
observability-stack   OutOfSync     Healthy

$ kubectl apply -f .\argocd\applications\observability-app.yaml
application.argoproj.io/observability-stack unchanged

$ kubectl annotate application observability-stack -n argocd  argocd.argoproj.io/refresh=hard --overwrite
application.argoproj.io/observability-stack annotated

shekk@Shekkar MINGW64 ~ (main)
$ kubectl get applications -n argocd
NAME                  SYNC STATUS   HEALTH STATUS
observability-stack   Synced        Healthy

