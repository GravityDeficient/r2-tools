# r2-sync Kubernetes example

A full manifest set for running r2-sync as a CronJob against an NFS-mounted source. All placeholder values — copy, customize, apply.

## Files

| File | Purpose |
|------|---------|
| `namespace.yaml` | Namespace for r2-sync resources |
| `nfs-pv.example.yaml` | NFS PersistentVolume (replace server + path) |
| `pvc.yaml` | PersistentVolumeClaim binding to the PV |
| `configmap.example.yaml` | Per-target sync config (one per CronJob) |
| `secret.example.yaml` | R2 credentials (manage via SOPS / Sealed Secrets / External Secrets in practice) |
| `cronjob.yaml` | The CronJob itself |

## Apply order

```
kubectl apply -f namespace.yaml
kubectl apply -f nfs-pv.example.yaml     # after editing
kubectl apply -f pvc.yaml
kubectl apply -f configmap.example.yaml  # after editing
kubectl apply -f secret.example.yaml     # via your secrets workflow
kubectl apply -f cronjob.yaml
```

## Multiple sync targets

The Namespace, PV, PVC, and Secret are shared across targets. Each target gets its own ConfigMap + CronJob pair. Duplicate `configmap.example.yaml` and `cronjob.yaml` for each target (rename the metadata.name, adjust the `configMap.name` reference and `schedule`).

## First-run check

After the first CronJob fires (or trigger it manually with `kubectl create job --from=cronjob/example-sync first-run`), check `kubectl logs` for:

- `{"source":"r2-sync","event":"start",...}` — wrapper started
- rclone JSON log lines (`"source":"rclone"`)
- `{"source":"r2-sync","event":"complete","files_transferred":N,"exit_code":0}` — success

If `files_transferred` is 0 and you expected data, check the pod's NFS read permissions (see the UID note at the top of `cronjob.yaml`).
