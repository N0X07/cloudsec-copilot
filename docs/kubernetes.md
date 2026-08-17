# Kubernetes Deployment Notes

These manifests are a local Kubernetes deployment option for the CloudSec
Copilot API. They are intended for kind or minikube portfolio validation, not a
production cluster.

Local validation status: the `k8s/base` manifests were applied successfully on
Docker Desktop with kind `0.32.0`; the Deployment rolled out with `1/1` ready
replica, and `/health` returned `{"status":"ok","environment":"kubernetes-local"}`
through `kubectl port-forward`.

The local manifest uses SQLite on an `emptyDir` volume so the API can start
without provisioning PostgreSQL. The AWS Terraform path remains the main
cloud-deployment template.

## Contents

- `k8s/base/namespace.yaml`: isolated namespace for the demo.
- `k8s/base/configmap.yaml`: non-secret runtime configuration.
- `k8s/base/secret.example.yaml`: placeholder secret shape for optional OpenAI
  access.
- `k8s/base/deployment.yaml`: one API replica with resource requests/limits,
  non-root security context, rolling update strategy, and health probes.
- `k8s/base/service.yaml`: internal ClusterIP service.

## Local validation with kind

```sh
kind create cluster --name cloudsec
docker build -t cloudsec-copilot:dev .
kind load docker-image cloudsec-copilot:dev --name cloudsec
kubectl apply -k k8s/base
kubectl -n cloudsec-copilot rollout status deployment/cloudsec-copilot-api
kubectl -n cloudsec-copilot get pods,svc
kubectl -n cloudsec-copilot port-forward svc/cloudsec-copilot-api 8000:8000
```

In another terminal:

```sh
python scripts/ops_healthcheck.py --url http://localhost:8000/health --expected-environment kubernetes-local
```

## Local validation with minikube

```sh
minikube start
eval "$(minikube docker-env)"
docker build -t cloudsec-copilot:dev .
kubectl apply -k k8s/base
kubectl -n cloudsec-copilot rollout status deployment/cloudsec-copilot-api
kubectl -n cloudsec-copilot port-forward svc/cloudsec-copilot-api 8000:8000
```

## Useful troubleshooting commands

```sh
kubectl -n cloudsec-copilot get pods -o wide
kubectl -n cloudsec-copilot describe pod -l app.kubernetes.io/component=api
kubectl -n cloudsec-copilot logs deploy/cloudsec-copilot-api --tail=100
kubectl -n cloudsec-copilot get endpoints cloudsec-copilot-api
kubectl -n cloudsec-copilot rollout history deployment/cloudsec-copilot-api
```

Common checks:

- `ImagePullBackOff`: confirm the image tag is `cloudsec-copilot:dev` and the
  image was loaded into kind or built inside the minikube Docker environment.
- Probe failures: port-forward the service and run `scripts/ops_healthcheck.py`.
- Permission errors on SQLite: confirm the pod has `fsGroup: 999` and the
  `/data` volume is mounted.
- Config mistakes: inspect `kubectl -n cloudsec-copilot describe deploy
  cloudsec-copilot-api` and compare environment values with `k8s/base`.

## Cleanup

```sh
kubectl delete -k k8s/base
kind delete cluster --name cloudsec
```
