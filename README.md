# CMPE 273 Module 6: Kubernetes Inventory Service

This project runs a small Flask inventory service on Kubernetes with 2 replicas behind a Service named `inventory`. A client Pod sends a request every second and logs which Pod answered. I tested load balancing, readiness probes, and what happens when a Pod is deleted.

## Files

```
app/inventory.py               Flask inventory service (port 8080)
app/client.py                  client that calls the Service every second
app/requirements.txt
Dockerfile                     one image for both scripts
k8s/inventory-deployment.yaml  2 replicas with readiness and liveness probes
k8s/inventory-service.yaml     ClusterIP Service named inventory
k8s/client-deployment.yaml     1 client replica
```

## How to deploy

### 1. Turn on Kubernetes

Open Docker Desktop, go to Settings > Kubernetes, turn on Kubernetes and pick the **kind** cluster type. Then check that it works:

```bash
kubectl config current-context    # docker-desktop
kubectl get nodes                 # desktop-control-plane   Ready
```

### 2. Build the image

```bash
docker build -t inventory-app:1.0 .
```

### 3. Make the image available to the kind cluster

A kind cluster runs inside its own container, so it can’t see the images in my local Docker. I didn’t have the `kind` tool installed, so I copied the image into the cluster with this command:

```bash
docker save inventory-app:1.0 | docker exec -i desktop-control-plane ctr -n k8s.io images import --all-platforms -
```

Check that the node has it:

```bash
docker exec desktop-control-plane crictl images | grep inventory
# docker.io/library/inventory-app   1.0   47a83c6cdd984   49.4MB
```

The Deployments use `imagePullPolicy: Never`, so Kubernetes uses this loaded image and never tries to pull from Docker Hub. If you rebuild the image, run the load command again.

### 4. Deploy

```bash
kubectl apply -f k8s/
kubectl get pods -o wide
```

### 5. Watch the client logs

```bash
kubectl logs -f deploy/client
```

### 6. Clean up

```bash
kubectl delete -f k8s/
```

Note for Git Bash on Windows: Git Bash changes paths like `/tmp/not-ready` into Windows paths. Run `export MSYS_NO_PATHCONV=1` before the `kubectl exec` commands below, or they will fail.

## Architecture

<img width="1800" height="680" alt="architecture (1)" src="https://github.com/user-attachments/assets/57031ebf-fa9d-4701-8c1b-d329cb73943b" />

## Evidence 1: Both replicas receive requests

```
$ kubectl apply -f k8s/
deployment.apps/client created
deployment.apps/inventory created
service/inventory created

$ kubectl get pods -o wide
NAME                         READY   STATUS    RESTARTS   AGE   IP           NODE                    NOMINATED NODE   READINESS GATES
client-7dc8df64b8-znbxd      1/1     Running   0          23s   10.244.0.5   desktop-control-plane   <none>           <none>
inventory-57446dfbd4-xqhbn   1/1     Running   0          22s   10.244.0.7   desktop-control-plane   <none>           <none>
inventory-57446dfbd4-zvc4s   1/1     Running   0          23s   10.244.0.6   desktop-control-plane   <none>           <none>

$ kubectl get svc inventory
NAME        TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)    AGE
inventory   ClusterIP   10.96.217.179   <none>        8080/TCP   24s

$ kubectl get endpoints inventory
Warning: v1 Endpoints is deprecated in v1.33+; use discovery.k8s.io/v1 EndpointSlice
NAME        ENDPOINTS                         AGE
inventory   10.244.0.6:8080,10.244.0.7:8080   23s
```

The pods really run the loaded image (same image ID as in the node):

```
client-7dc8df64b8-znbxd    sha256:47a83c6cdd98414295ede0b4cf014c392f31370f2acd787e22dda950d2f74cbd
inventory-57446dfbd4-xqhbn sha256:47a83c6cdd98414295ede0b4cf014c392f31370f2acd787e22dda950d2f74cbd
inventory-57446dfbd4-zvc4s sha256:47a83c6cdd98414295ede0b4cf014c392f31370f2acd787e22dda950d2f74cbd
```

Client logs. Answers come from both `xqhbn` and `zvc4s`:

```
$ kubectl logs deploy/client --tail=15
2026-11-02 14:04:39,855 status=200 item=apple stock=10 pod=inventory-57446dfbd4-xqhbn
2026-11-02 14:04:40,859 status=200 item=apple stock=10 pod=inventory-57446dfbd4-xqhbn
2026-11-02 14:04:41,863 status=200 item=apple stock=10 pod=inventory-57446dfbd4-zvc4s
2026-11-02 14:04:42,867 status=200 item=apple stock=10 pod=inventory-57446dfbd4-xqhbn
2026-11-02 14:04:43,872 status=200 item=apple stock=10 pod=inventory-57446dfbd4-zvc4s
2026-11-02 14:04:44,876 status=200 item=apple stock=10 pod=inventory-57446dfbd4-zvc4s
2026-11-02 14:04:45,880 status=200 item=apple stock=10 pod=inventory-57446dfbd4-xqhbn
2026-11-02 14:04:46,885 status=200 item=apple stock=10 pod=inventory-57446dfbd4-zvc4s
2026-11-02 14:04:47,889 status=200 item=apple stock=10 pod=inventory-57446dfbd4-zvc4s
2026-11-02 14:04:48,893 status=200 item=apple stock=10 pod=inventory-57446dfbd4-xqhbn
2026-11-02 14:04:49,897 status=200 item=apple stock=10 pod=inventory-57446dfbd4-xqhbn
2026-11-02 14:04:50,901 status=200 item=apple stock=10 pod=inventory-57446dfbd4-xqhbn
2026-11-02 14:04:51,904 status=200 item=apple stock=10 pod=inventory-57446dfbd4-xqhbn
2026-11-02 14:04:52,908 status=200 item=apple stock=10 pod=inventory-57446dfbd4-xqhbn
2026-11-02 14:04:53,912 status=200 item=apple stock=10 pod=inventory-57446dfbd4-zvc4s
```

The logs show that both Pods are getting requests. The requests do not switch between the two Pods in an exact order, but both Pods answer over time.

## Evidence 2: Readiness failure and recovery

I made pod `xqhbn` fail its readiness probe by creating the file `/tmp/not-ready`:

```
$ kubectl exec inventory-57446dfbd4-xqhbn -- touch /tmp/not-ready

$ kubectl get pods
NAME                         READY   STATUS    RESTARTS   AGE
client-7dc8df64b8-znbxd      1/1     Running   0          74s
inventory-57446dfbd4-xqhbn   0/1     Running   0          73s
inventory-57446dfbd4-zvc4s   1/1     Running   0          74s

$ kubectl get endpoints inventory
NAME        ENDPOINTS         AGE
inventory   10.244.0.6:8080   73s
```

The not ready Pod returns 503 for `/ready`, but `/health` still returns 200. The Pod stays running, but Kubernetes does not send client requests to it.

```
$ kubectl logs deploy/client --tail=10
2026-11-02 14:05:43,171 status=200 item=apple stock=10 pod=inventory-57446dfbd4-zvc4s
2026-11-02 14:05:44,178 status=200 item=apple stock=10 pod=inventory-57446dfbd4-zvc4s
2026-11-02 14:05:45,194 status=200 item=apple stock=10 pod=inventory-57446dfbd4-zvc4s
2026-11-02 14:05:46,198 status=200 item=apple stock=10 pod=inventory-57446dfbd4-zvc4s
2026-11-02 14:05:47,205 status=200 item=apple stock=10 pod=inventory-57446dfbd4-zvc4s
2026-11-02 14:05:48,210 status=200 item=apple stock=10 pod=inventory-57446dfbd4-zvc4s
2026-11-02 14:05:49,215 status=200 item=apple stock=10 pod=inventory-57446dfbd4-zvc4s
2026-11-02 14:05:50,219 status=200 item=apple stock=10 pod=inventory-57446dfbd4-zvc4s
2026-11-02 14:05:51,223 status=200 item=apple stock=10 pod=inventory-57446dfbd4-zvc4s
2026-11-02 14:05:52,227 status=200 item=apple stock=10 pod=inventory-57446dfbd4-zvc4s
```

The pod logs also show that `/ready` returns 503 while `/health` still returns 200::

```
$ kubectl logs inventory-57446dfbd4-xqhbn --tail=4
2026-11-02 14:05:48,074 pod=inventory-57446dfbd4-xqhbn endpoint=/ready status=503
2026-11-02 14:05:50,074 pod=inventory-57446dfbd4-xqhbn endpoint=/ready status=503
2026-11-02 14:05:51,371 pod=inventory-57446dfbd4-xqhbn endpoint=/health status=200
2026-11-02 14:05:52,074 pod=inventory-57446dfbd4-xqhbn endpoint=/ready status=503
```

Then I removed the file to make the pod ready again:

```
$ kubectl exec inventory-57446dfbd4-xqhbn -- rm /tmp/not-ready

$ kubectl get pods
NAME                         READY   STATUS    RESTARTS   AGE
client-7dc8df64b8-znbxd      1/1     Running   0          89s
inventory-57446dfbd4-xqhbn   1/1     Running   0          88s
inventory-57446dfbd4-zvc4s   1/1     Running   0          89s

$ kubectl get endpoints inventory
NAME        ENDPOINTS                         AGE
inventory   10.244.0.6:8080,10.244.0.7:8080   88s

$ kubectl logs deploy/client --tail=10
2026-11-02 14:05:58,254 status=200 item=apple stock=10 pod=inventory-57446dfbd4-zvc4s
2026-11-02 14:05:59,259 status=200 item=apple stock=10 pod=inventory-57446dfbd4-zvc4s
2026-11-02 14:06:00,265 status=200 item=apple stock=10 pod=inventory-57446dfbd4-zvc4s
2026-11-02 14:06:01,270 status=200 item=apple stock=10 pod=inventory-57446dfbd4-xqhbn
2026-11-02 14:06:02,275 status=200 item=apple stock=10 pod=inventory-57446dfbd4-zvc4s
2026-11-02 14:06:03,280 status=200 item=apple stock=10 pod=inventory-57446dfbd4-xqhbn
2026-11-02 14:06:04,286 status=200 item=apple stock=10 pod=inventory-57446dfbd4-zvc4s
2026-11-02 14:06:05,286 status=200 item=apple stock=10 pod=inventory-57446dfbd4-zvc4s
2026-11-02 14:06:06,290 status=200 item=apple stock=10 pod=inventory-57446dfbd4-zvc4s
2026-11-02 14:06:07,295 status=200 item=apple stock=10 pod=inventory-57446dfbd4-zvc4s
```

The pod is back to 1/1, both IPs are in the endpoints again, and `xqhbn` starts answering again.

## Evidence 3: Pod deletion and replacement

Before:

```
$ kubectl get pods
NAME                         READY   STATUS    RESTARTS   AGE
client-7dc8df64b8-znbxd      1/1     Running   0          103s
inventory-57446dfbd4-xqhbn   1/1     Running   0          102s
inventory-57446dfbd4-zvc4s   1/1     Running   0          103s

$ kubectl get svc inventory
NAME        TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)    AGE
inventory   ClusterIP   10.96.217.179   <none>        8080/TCP   103s
```

Delete one pod:

```
$ kubectl delete pod inventory-57446dfbd4-zvc4s
pod "inventory-57446dfbd4-zvc4s" deleted from default namespace
```

After:

```
$ kubectl get pods
NAME                         READY   STATUS    RESTARTS   AGE
client-7dc8df64b8-znbxd      1/1     Running   0          2m30s
inventory-57446dfbd4-s7sw9   1/1     Running   0          46s
inventory-57446dfbd4-xqhbn   1/1     Running   0          2m29s

$ kubectl get svc inventory
NAME        TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)    AGE
inventory   ClusterIP   10.96.217.179   <none>        8080/TCP   2m31s

$ kubectl get endpoints inventory
NAME        ENDPOINTS                         AGE
inventory   10.244.0.7:8080,10.244.0.8:8080   2m30s
```

Kubernetes created a new Pod `s7sw9` with a new IP (10.244.0.8). There are still 2 Pods, and the Service name and ClusterIP did not change.

The client kept working while the Pod was being replaced. For a few seconds, `xqhbn` answered the requests by itself. After the new Pod `s7sw9` started, both Pods answered requests again.

```
2026-11-02 14:06:10,315 status=200 item=apple stock=10 pod=inventory-57446dfbd4-zvc4s
2026-11-02 14:06:11,322 status=200 item=apple stock=10 pod=inventory-57446dfbd4-xqhbn
2026-11-02 14:06:12,329 status=200 item=apple stock=10 pod=inventory-57446dfbd4-xqhbn
2026-11-02 14:06:13,334 status=200 item=apple stock=10 pod=inventory-57446dfbd4-zvc4s
2026-11-02 14:06:14,339 status=200 item=apple stock=10 pod=inventory-57446dfbd4-xqhbn
2026-11-02 14:06:15,344 status=200 item=apple stock=10 pod=inventory-57446dfbd4-xqhbn
2026-11-02 14:06:16,348 status=200 item=apple stock=10 pod=inventory-57446dfbd4-xqhbn
2026-11-02 14:06:17,352 status=200 item=apple stock=10 pod=inventory-57446dfbd4-xqhbn
2026-11-02 14:06:18,357 status=200 item=apple stock=10 pod=inventory-57446dfbd4-xqhbn
2026-11-02 14:06:19,361 status=200 item=apple stock=10 pod=inventory-57446dfbd4-s7sw9
2026-11-02 14:06:20,367 status=200 item=apple stock=10 pod=inventory-57446dfbd4-xqhbn
2026-11-02 14:06:21,373 status=200 item=apple stock=10 pod=inventory-57446dfbd4-xqhbn
2026-11-02 14:06:22,377 status=200 item=apple stock=10 pod=inventory-57446dfbd4-s7sw9
2026-11-02 14:06:23,381 status=200 item=apple stock=10 pod=inventory-57446dfbd4-s7sw9
2026-11-02 14:06:24,386 status=200 item=apple stock=10 pod=inventory-57446dfbd4-s7sw9
2026-11-02 14:06:25,393 status=200 item=apple stock=10 pod=inventory-57446dfbd4-xqhbn
2026-11-02 14:06:26,398 status=200 item=apple stock=10 pod=inventory-57446dfbd4-s7sw9
2026-11-02 14:06:27,403 status=200 item=apple stock=10 pod=inventory-57446dfbd4-xqhbn
2026-11-02 14:06:28,409 status=200 item=apple stock=10 pod=inventory-57446dfbd4-s7sw9
```

The `kubectl delete` command took about 30 seconds to finish. During this time, the client still worked and I did not see any request errors.

## Reflection

I learned why a Kubernetes Service is useful when there are multiple Pods. Pod names and IP addresses can change, so the client should not connect to one Pod directly. The client can use the Service name instead.

I also saw this in my tests. When I deleted one Pod, Kubernetes created a new one, but the client kept working with the same Service. When one Pod was not ready, the Service only sent requests to the other ready Pod.
