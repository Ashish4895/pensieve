# GHCR Publish + EC2 Images Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Delete Render/root packaging, add a separate GHCR publish workflow on `main`, and ship `docker-compose.prod.yml` for EC2 pulls.

**Architecture:** PR checks stay as-is. A new `publish-ghcr.yml` builds and pushes `backend` / `celery` / `nginx` images from `docker/*` Dockerfiles. Production Compose references those GHCR images; local `docker-compose.yml` keeps `build:`.

**Tech Stack:** GitHub Actions, Docker Buildx, GHCR, Docker Compose.

## Global Constraints

- Approach B: separate pipeline; do not fold publish into `pr-checks.yml`.
- Do not re-run pytest/Vitest in publish workflow.
- No EC2 SSH auto-deploy from Actions.
- Image names: `ghcr.io/<lowercase-owner>/pensieve-{backend,celery,nginx}`.
- Tags: `latest` and `sha-<7-char-sha>`.
- Delete: root `Dockerfile`, `render.yaml`, `scripts/render-cutover.sh`.
- Spec: `docs/superpowers/specs/2026-09-09-ghcr-ec2-publish-design.md`.
- Owner for checked-in compose defaults: `ashish4895` (override via env if forked).

---

## File map

| File | Action |
|------|--------|
| `Dockerfile` | Delete |
| `render.yaml` | Delete |
| `scripts/render-cutover.sh` | Delete |
| `.github/workflows/publish-ghcr.yml` | Create |
| `docker-compose.prod.yml` | Create |
| `README.md` | Replace Render deploy section |
| `AGENTS.md` | Note publish + prod compose |
| Spec status line | Mark Approved — implemented |

---

### Task 1: Remove Render / root Dockerfile

**Files:**
- Delete: `Dockerfile`, `render.yaml`, `scripts/render-cutover.sh`

**Interfaces:**
- Consumes: none
- Produces: repo no longer references root all-in-one image for deploy

- [ ] **Step 1: Confirm references**

```bash
cd /Users/ashishsingh/Project/pensieve
rg -n 'render\.yaml|dockerfilePath: \./Dockerfile|^FROM node:22' Dockerfile render.yaml README.md AGENTS.md || true
ls -la Dockerfile render.yaml scripts/render-cutover.sh
```

- [ ] **Step 2: Delete the three files**

```bash
git rm Dockerfile render.yaml scripts/render-cutover.sh
```

- [ ] **Step 3: Commit**

```bash
git commit -m "chore: drop Render all-in-one Dockerfile and blueprint"
```

---

### Task 2: Add `publish-ghcr.yml`

**Files:**
- Create: `.github/workflows/publish-ghcr.yml`

**Interfaces:**
- Consumes: `docker/backend/Dockerfile`, `docker/celery/Dockerfile`, `docker/nginx/Dockerfile`, repo root context
- Produces: GHCR images tagged `latest` and `sha-*`

- [ ] **Step 1: Create the workflow with this exact content**

```yaml
name: Publish GHCR

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  packages: write

jobs:
  publish:
    name: publish-${{ matrix.name }}
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        include:
          - name: backend
            file: docker/backend/Dockerfile
            image: pensieve-backend
          - name: celery
            file: docker/celery/Dockerfile
            image: pensieve-celery
          - name: nginx
            file: docker/nginx/Dockerfile
            image: pensieve-nginx
    steps:
      - uses: actions/checkout@v4

      - name: Image metadata
        id: meta
        run: |
          OWNER=$(echo '${{ github.repository_owner }}' | tr '[:upper:]' '[:lower:]')
          SHA=$(echo '${{ github.sha }}' | cut -c1-7)
          echo "owner=${OWNER}" >> "$GITHUB_OUTPUT"
          echo "tags=ghcr.io/${OWNER}/${{ matrix.image }}:latest,ghcr.io/${OWNER}/${{ matrix.image }}:sha-${SHA}" >> "$GITHUB_OUTPUT"

      - uses: docker/setup-buildx-action@v3

      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - uses: docker/build-push-action@v6
        with:
          context: .
          file: ${{ matrix.file }}
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          cache-from: type=gha,scope=${{ matrix.name }}
          cache-to: type=gha,mode=max,scope=${{ matrix.name }}
```

- [ ] **Step 2: YAML sanity**

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/publish-ghcr.yml'))" 2>/dev/null \
  || python3 -c "print('skip pyyaml'); open('.github/workflows/publish-ghcr.yml').read()"
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/publish-ghcr.yml
git commit -m "ci: publish backend celery nginx images to GHCR on main"
```

---

### Task 3: Add `docker-compose.prod.yml`

**Files:**
- Create: `docker-compose.prod.yml`

**Interfaces:**
- Consumes: GHCR image names from Task 2; same env contract as `docker-compose.yml`
- Produces: EC2 pull/up without build

- [ ] **Step 1: Create prod compose**

Use owner `ashish4895`. Keep db/redis from Hub. App services: `image` only (no `build`). Mirror env/depends_on/ports from `docker-compose.yml`.

```yaml
name: pensieve-platform

services:
  db:
    image: pgvector/pgvector:pg16
    restart: unless-stopped
    environment:
      POSTGRES_DB: pensieve
      POSTGRES_USER: pensieve
      POSTGRES_PASSWORD: pensieve
    ports:
      - "5434:5432"
    volumes:
      - pensieve_platform_pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U pensieve -d pensieve"]
      interval: 5s
      timeout: 5s
      retries: 10

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    ports:
      - "6380:6379"
    volumes:
      - pensieve_platform_redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 10

  backend:
    image: ghcr.io/ashish4895/pensieve-backend:${PENSIVE_IMAGE_TAG:-latest}
    restart: unless-stopped
    ports:
      - "8001:8000"
    environment:
      DATABASE_URL: postgres://pensieve:pensieve@db:5432/pensieve
      REDIS_URL: redis://redis:6379/0
      DJANGO_SECRET_KEY: ${DJANGO_SECRET_KEY:?DJANGO_SECRET_KEY must be set}
      GEMINI_API_KEY: ${GEMINI_API_KEY:-}
      DEBUG: ${DEBUG:-false}
      ALLOWED_HOSTS: ${ALLOWED_HOSTS:-localhost,127.0.0.1,backend,nginx}
      CORS_ALLOWED_ORIGINS: ${CORS_ALLOWED_ORIGINS:-http://127.0.0.1:8080,http://localhost:8080}
      CSRF_TRUSTED_ORIGINS: ${CSRF_TRUSTED_ORIGINS:-http://127.0.0.1:8080,http://localhost:8080}
      PORT: "8000"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  celery-worker:
    image: ghcr.io/ashish4895/pensieve-celery:${PENSIVE_IMAGE_TAG:-latest}
    restart: unless-stopped
    environment:
      DATABASE_URL: postgres://pensieve:pensieve@db:5432/pensieve
      REDIS_URL: redis://redis:6379/0
      DJANGO_SECRET_KEY: ${DJANGO_SECRET_KEY:?DJANGO_SECRET_KEY must be set}
      GEMINI_API_KEY: ${GEMINI_API_KEY:-}
      DEBUG: ${DEBUG:-false}
      CELERY_ROLE: worker
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  celery-beat:
    image: ghcr.io/ashish4895/pensieve-celery:${PENSIVE_IMAGE_TAG:-latest}
    restart: unless-stopped
    environment:
      DATABASE_URL: postgres://pensieve:pensieve@db:5432/pensieve
      REDIS_URL: redis://redis:6379/0
      DJANGO_SECRET_KEY: ${DJANGO_SECRET_KEY:?DJANGO_SECRET_KEY must be set}
      DEBUG: ${DEBUG:-false}
      CELERY_ROLE: beat
    depends_on:
      redis:
        condition: service_healthy

  nginx:
    image: ghcr.io/ashish4895/pensieve-nginx:${PENSIVE_IMAGE_TAG:-latest}
    restart: unless-stopped
    ports:
      - "8080:80"
    depends_on:
      - backend

volumes:
  pensieve_platform_pgdata:
  pensieve_platform_redisdata:
```

- [ ] **Step 2: Validate compose file parses**

```bash
docker compose -f docker-compose.prod.yml config >/dev/null
```

Expected: exit 0 (may warn if `.env` missing `DJANGO_SECRET_KEY` — set a dummy in env for the check: `DJANGO_SECRET_KEY=x docker compose -f docker-compose.prod.yml config >/dev/null`).

- [ ] **Step 3: Commit**

```bash
git add docker-compose.prod.yml
git commit -m "chore: add prod compose that pulls GHCR images"
```

---

### Task 4: Docs + mark spec implemented

**Files:**
- Modify: `README.md` (Deploy section)
- Modify: `AGENTS.md`
- Modify: `docs/superpowers/specs/2026-09-09-ghcr-ec2-publish-design.md` status

- [ ] **Step 1: Replace README “Deploy (Render)” with**

```markdown
## Deploy (EC2 + GHCR)

App images are published to GHCR on every push to `main` (`.github/workflows/publish-ghcr.yml`):

- `ghcr.io/ashish4895/pensieve-backend`
- `ghcr.io/ashish4895/pensieve-celery`
- `ghcr.io/ashish4895/pensieve-nginx`

Tags: `latest` and `sha-<short>`. After the first publish, set each package visibility to **Public** (GitHub → Packages) so the EC2 host can pull without `docker login`. If packages stay private, create a read-only PAT and run `docker login ghcr.io` on the instance.

On the EC2 host (with Docker + Compose, enough disk, and a `.env`):

```bash
cd ~/pensieve
git pull
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

Point `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, and `CSRF_TRUSTED_ORIGINS` at the instance public URL (e.g. `http://<eip>:8080`). Optional pin: `PENSIVE_IMAGE_TAG=sha-abcdef1`.

Local development still uses `docker compose up --build` (build from `docker/*`).
```

- [ ] **Step 2: Add AGENTS.md bullet under Commands**

```markdown
- GHCR publish: `.github/workflows/publish-ghcr.yml` pushes backend/celery/nginx on `main`. EC2: `docker compose -f docker-compose.prod.yml pull && up -d`.
```

- [ ] **Step 3: Spec status → `Approved — implemented`**

- [ ] **Step 4: Commit**

```bash
git add README.md AGENTS.md docs/superpowers/specs/2026-09-09-ghcr-ec2-publish-design.md
git commit -m "docs: EC2 GHCR deploy; mark publish design implemented"
```

---

### Task 5: Ship via PR and verify Actions

**Files:** none (git/gh)

- [ ] **Step 1: Push branch and open PR** (do not push straight to `main` if protection requires PR)

```bash
git checkout -b feat/ghcr-ec2-publish
git push -u origin HEAD
gh pr create --title "ci: publish Compose images to GHCR; drop Render packaging" --body "## Summary
- Remove root Dockerfile + Render blueprint
- Add publish-ghcr.yml for backend/celery/nginx
- Add docker-compose.prod.yml for EC2 pulls

## Test plan
- [ ] PR checks green
- [ ] After merge, Publish GHCR workflow succeeds
- [ ] Packages visible; EC2 can pull
"
```

- [ ] **Step 2: After merge, confirm workflow**

```bash
gh run list --workflow=publish-ghcr.yml --limit 3
```

Expected: success for three matrix jobs.

- [ ] **Step 3: Make packages public (once)** via GitHub UI or document for user.

---

## Spec coverage

| Spec § | Task |
|--------|------|
| §4 Cleanup | Task 1 + 4 |
| §5 Publish workflow | Task 2 |
| §6 EC2 Compose | Task 3 |
| §7 Separate from PR checks | Task 2 (no pr-checks edit) |
| Success criteria | Task 5 |

## Placeholder scan

None.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-09-ghcr-ec2-publish.md`. Two execution options:

**1. Subagent-Driven (recommended)** — fresh subagent per task  
**2. Inline Execution** — this session  

Which approach?
