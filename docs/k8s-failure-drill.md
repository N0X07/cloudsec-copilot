# Kubernetes Failure Drill

This drill documents common local Kubernetes failure scenarios for CloudSec
Copilot. It is designed for kind/minikube validation and interview discussion,
not as a claim of production incident response.

Baseline validation already completed:

- Docker Desktop was started locally.
- `kind 0.32.0` created the `cloudsec` cluster.
- `cloudsec-copilot:dev` was built and loaded into kind.
- `kubectl apply -k k8s/base` created the namespace, config, secret, service,
  and deployment.
- `kubectl -n cloudsec-copilot rollout status deployment/cloudsec-copilot-api`
  completed successfully.
- `/health` returned `{"status":"ok","environment":"kubernetes-local"}` through
  `kubectl port-forward`.

## Scenario 1: ImagePullBackOff

Purpose: verify image-tag and pod-event troubleshooting.

Local drill status: completed on the `cloudsec` kind cluster. Setting the image
to `cloudsec-copilot:missing` produced a new pod in `ImagePullBackOff`, while
the previous ready pod stayed available during rolling update. Restoring the
image to `cloudsec-copilot:dev` completed `rollout status` successfully.

Inject:

```sh
kubectl -n cloudsec-copilot set image deployment/cloudsec-copilot-api api=cloudsec-copilot:missing
kubectl -n cloudsec-copilot rollout status deployment/cloudsec-copilot-api --timeout=45s
```

Observe:

```sh
kubectl -n cloudsec-copilot get pods
kubectl -n cloudsec-copilot describe pod -l app.kubernetes.io/component=api
```

Expected evidence:

- Pod event mentions image pull failure.
- Pod status becomes `ImagePullBackOff` or `ErrImagePull`.

Recover:

```sh
kubectl -n cloudsec-copilot set image deployment/cloudsec-copilot-api api=cloudsec-copilot:dev
kubectl -n cloudsec-copilot rollout status deployment/cloudsec-copilot-api
```

## Scenario 2: Probe failure

Purpose: verify readiness/liveness probe diagnosis.

Inject by temporarily changing the probe path in `k8s/base/deployment.yaml` from
`/health` to `/missing-health`, then apply:

```sh
kubectl apply -k k8s/base
kubectl -n cloudsec-copilot rollout status deployment/cloudsec-copilot-api --timeout=60s
```

Observe:

```sh
kubectl -n cloudsec-copilot describe pod -l app.kubernetes.io/component=api
kubectl -n cloudsec-copilot logs deploy/cloudsec-copilot-api --tail=100
kubectl -n cloudsec-copilot get endpoints cloudsec-copilot-api
```

Expected evidence:

- Pod events show readiness or liveness probe failures.
- The service has no ready endpoint while readiness fails.

Recover:

```sh
git diff k8s/base/deployment.yaml
# Restore probe path to /health.
kubectl apply -k k8s/base
kubectl -n cloudsec-copilot rollout status deployment/cloudsec-copilot-api
```

## Scenario 3: Config missing

Purpose: verify runtime config and environment debugging.

Inject by temporarily setting an invalid `DATABASE_URL` in
`k8s/base/configmap.yaml`, then apply:

```sh
kubectl apply -k k8s/base
kubectl -n cloudsec-copilot rollout status deployment/cloudsec-copilot-api --timeout=60s
```

Observe:

```sh
kubectl -n cloudsec-copilot describe pod -l app.kubernetes.io/component=api
kubectl -n cloudsec-copilot logs deploy/cloudsec-copilot-api --tail=100
kubectl -n cloudsec-copilot get configmap cloudsec-copilot-config -o yaml
```

Recover:

```sh
# Restore DATABASE_URL to sqlite:////data/cloudsec.db.
kubectl apply -k k8s/base
kubectl -n cloudsec-copilot rollout status deployment/cloudsec-copilot-api
```

## Scenario 4: Service access issue

Purpose: verify service selector and port-forward debugging.

Observe:

```sh
kubectl -n cloudsec-copilot get svc cloudsec-copilot-api -o yaml
kubectl -n cloudsec-copilot get endpoints cloudsec-copilot-api
kubectl -n cloudsec-copilot port-forward svc/cloudsec-copilot-api 8000:8000
cloudsecctl health --url http://localhost:8000/health --expected-environment kubernetes-local
```

Expected evidence:

- Service selector matches pod labels.
- Endpoints contain the ready pod IP and port.
- `cloudsecctl health` returns OK through port-forward.

## Cleanup

```sh
kubectl delete -k k8s/base
kind delete cluster --name cloudsec
```
