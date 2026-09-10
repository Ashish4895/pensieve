# Deploy EC2 Pipeline Design

**Date:** 2026-09-10  
**Status:** Draft — awaiting user review  
**Approach:** A — separate `deploy-ec2.yml` via `workflow_run` after Publish GHCR  
**Product:** Pensieve

## 1. Context

Pipelines today:

1. **PR checks** — `.github/workflows/pr-checks.yml` (tests on PRs)  
2. **Publish GHCR** — `.github/workflows/publish-ghcr.yml` (images on `main`)  

EC2 is the runtime. Deploy was explicitly out of scope of the GHCR design. Operators currently SSH (including Cursor Remote SSH) and run Compose pull/up by hand. This design automates that over SSH from GitHub Actions, reusing the same host access pattern—not Cursor’s Remote SSH feature itself.

## 2. Goals

- Third, separate workflow that deploys to EC2 only after a successful GHCR publish on `main`.
- Support manual redeploy via `workflow_dispatch`.
- Keep publish and deploy independently disable-able.

## 3. Non-goals

- Provisioning EC2, security groups, disk growth, or first-time `.env` bootstrap.
- AWS SSM / self-hosted runners.
- Blue-green, canary, or automated rollback.
- Folding deploy into `publish-ghcr.yml` as a dependent job.

## 4. Trigger

**File:** `.github/workflows/deploy-ec2.yml`

```yaml
on:
  workflow_run:
    workflows: ["Publish GHCR"]
    types: [completed]
  workflow_dispatch:
```

**Guards (job `if`):**

- `workflow_dispatch` → always allow.  
- `workflow_run` → require `github.event.workflow_run.conclusion == 'success'` and `github.event.workflow_run.head_branch == 'main'`.

Note: `workflow_run` jobs use the default branch’s workflow file. The deploy YAML must land on `main` before auto-deploy works.

## 5. Job

| Item | Value |
|------|--------|
| Name | `deploy` |
| Runner | `ubuntu-latest` |
| Checkout | Not required for app code (commands run on EC2) |

**Steps:**

1. Install SSH client (preinstalled on ubuntu-latest).  
2. Write private key from secret to a temp file (`0600`), or use `webfactory/ssh-agent` / `appleboy/ssh-action`. Prefer a well-known action (`appleboy/ssh-action@v1`) to avoid hand-rolled known_hosts mistakes—or `ssh-keyscan` + `ssh` for YAGNI.  
3. Remote script (non-interactive):

```bash
set -euo pipefail
cd "${EC2_APP_DIR:-$HOME/pensieve}"
git fetch origin main
git checkout main
git pull --ff-only origin main
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps
```

Pin image tag optionally later via `PENSIVE_IMAGE_TAG=sha-…` from the triggering publish SHA; **v1 uses `latest`** after pull (images just published).

## 6. Secrets and variables

| Name | Required | Purpose |
|------|----------|---------|
| `EC2_HOST` | yes | Public IP or DNS |
| `EC2_USER` | yes | e.g. `ubuntu` |
| `EC2_SSH_KEY` | yes | Full PEM private key (same key used for Cursor Remote SSH) |
| `EC2_PORT` | no | Default `22` |
| `EC2_APP_DIR` | no | Default `~/pensieve` (expand on remote) |

Store under GitHub → Settings → Secrets and variables → Actions. Never commit the key.

## 7. EC2 preconditions

- Docker Engine + Compose plugin installed; user in `docker` group or use `sudo` in the remote script (prefer docker group).  
- Clone at app dir; `.env` configured for production.  
- GHCR images pullable (packages public, or `docker login ghcr.io` already done on host).  
- `git pull` works for `ubuntu` (public HTTPS clone of `Ashish4895/pensieve`, or deploy key).  
- Enough disk for pulled layers.

## 8. Pipeline relationship

```text
PR → pr-checks → merge to main
main push → Publish GHCR (backend + nginx)
         → (success) Deploy EC2 (SSH pull/up)
```

Manual: Actions → Deploy EC2 → Run workflow.

## 9. Security notes

- Restrict SG SSH to GitHub Actions IP ranges is impractical (dynamic); prefer key-only auth, disable password login, consider later SSM.  
- Key in Actions secrets has host access—rotate if leaked; use a dedicated deploy key, not a personal master key, when practical.  
- Do not echo secrets in logs; `appleboy/ssh-action` script should avoid printing `.env`.

## 10. Docs

- `README.md` Deploy section: mention auto-deploy after GHCR + required secrets.  
- `AGENTS.md`: one line for the third pipeline.

## 11. Success criteria

- Successful Publish GHCR on `main` starts Deploy EC2 and leaves containers updated (`ps` healthy/up).  
- Failed publish does not deploy.  
- Manual `workflow_dispatch` redeploys without a new image build.  
- PR checks and publish workflows unchanged except docs cross-links.
