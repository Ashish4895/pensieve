# GHCR Publish + EC2 Images Design

**Date:** 2026-09-09  
**Status:** Approved — implemented  
**Approach:** B — separate publish pipeline (not folded into PR checks)  
**Product:** Pensieve

## 1. Context

PR checks already run on pull requests (`.github/workflows/pr-checks.yml`). Deploy target is **EC2** via Compose, not Render. The root `Dockerfile` exists only for Render’s all-in-one web image; Compose already builds from `docker/backend`, `docker/celery`, and `docker/nginx`.

## 2. Goals

- Remove Render-oriented packaging (root `Dockerfile`, `render.yaml`, cutover script).
- On every push to `main`, publish the three Compose app images to GitHub Container Registry (GHCR).
- Provide a production Compose file so EC2 pulls pre-built images instead of building on the instance.
- Keep PR test workflow unchanged and separate.

## 3. Non-goals

- Re-running pytest/Vitest inside the publish workflow (branch protection + PR checks gate merges).
- Automatic SSH/deploy to EC2 from Actions.
- Publishing `db` / `redis` images (continue using Hub images `pgvector/pgvector:pg16` and `redis:7-alpine`).
- Changing local-dev `docker-compose.yml` build behavior (devs still `build:` locally).

## 4. Cleanup

Delete:

- `Dockerfile` (root)
- `render.yaml`
- `scripts/render-cutover.sh`

Update docs:

- `README.md` — replace “Deploy (Render)” with EC2 + GHCR pull instructions.
- `AGENTS.md` — note publish workflow; drop Render-only wording if any.

## 5. Publish workflow

**File:** `.github/workflows/publish-ghcr.yml`

**Triggers:**

```yaml
on:
  push:
    branches: [main]
  workflow_dispatch:
```

**Permissions:**

```yaml
permissions:
  contents: read
  packages: write
```

**Auth:** `docker/login-action` to `ghcr.io` with `github.actor` + `secrets.GITHUB_TOKEN`.

**Strategy:** one job, matrix over three images (parallel):

| Matrix id | Image name | Dockerfile |
|-----------|------------|------------|
| backend | `ghcr.io/<owner>/pensieve-backend` | `docker/backend/Dockerfile` |
| celery | `ghcr.io/<owner>/pensieve-celery` | `docker/celery/Dockerfile` |
| nginx | `ghcr.io/<owner>/pensieve-nginx` | `docker/nginx/Dockerfile` |

- **Context:** repository root (`.`) — Dockerfiles already `COPY services/...` and `docker/...`.
- **Tags:** `latest` and `sha-<github.sha[0:7]>`.
- **Owner:** lowercase `github.repository_owner` (GHCR requires lowercase).
- **Buildx:** `docker/setup-buildx-action` + `docker/build-push-action` with `push: true`, GHA cache when cheap to enable.

**Package visibility:** first push creates packages under the user/org. Prefer **public** packages so EC2 needs no `docker login` (document how to set public in GitHub Packages UI, or use `gh api` once). If left private, EC2 must `echo $CR_PAT | docker login ghcr.io -u USER --password-stdin` with a read-only PAT.

## 6. EC2 Compose

**File:** `docker-compose.prod.yml`

- Same service graph as `docker-compose.yml` (db, redis, backend, celery-worker, celery-beat, nginx).
- App services use `image:` instead of `build:`:

```yaml
backend:
  image: ghcr.io/<owner>/pensieve-backend:${PENSIVE_IMAGE_TAG:-latest}
celery-worker:
  image: ghcr.io/<owner>/pensieve-celery:${PENSIVE_IMAGE_TAG:-latest}
celery-beat:
  image: ghcr.io/<owner>/pensieve-celery:${PENSIVE_IMAGE_TAG:-latest}
nginx:
  image: ghcr.io/<owner>/pensieve-nginx:${PENSIVE_IMAGE_TAG:-latest}
```

- Env vars remain via `.env` on the host (`DJANGO_SECRET_KEY`, `GEMINI_API_KEY`, `ALLOWED_HOSTS`, CORS/CSRF for the EC2 public URL, etc.).
- Host ports: keep **8080** for nginx (edge); db/redis ports optional (can omit host publish in prod for tighter security — default: match current compose for simplicity unless noted in plan as optional harden).

**EC2 operator loop:**

```bash
cd ~/pensieve
git pull   # for compose/env templates only
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

## 7. Relationship to PR checks

```text
PR  → pr-checks.yml (backend + frontend) → merge only if green (branch protection)
main push → publish-ghcr.yml (build/push images)  [separate pipeline]
EC2 → pull images + up -d
```

Publish does **not** depend on a workflow_run of PR checks (Approach B). Correctness relies on not pushing broken code to `main` without CI.

## 8. Success criteria

- Root `Dockerfile` / Render blueprint / cutover script gone.
- Merge (or push) to `main` produces three GHCR packages with `latest` + sha tags.
- EC2 can run the stack with `docker-compose.prod.yml` without building.
- PR checks workflow still runs only on pull requests.

## 9. Risks

- Admin merge bypassing required checks can publish untested images — acceptable under Approach B; mitigate with branch protection.
- Private GHCR packages block EC2 pulls until login — document public packages or PAT.
- Disk on EC2 still matters for pulled layers (grow volume as previously discussed).
