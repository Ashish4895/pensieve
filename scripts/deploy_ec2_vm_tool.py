#!/usr/bin/env python3
"""Deploy Pensieve to EC2 via vm_tool cloud SSH setup.

Requires:
  pip install vm-tool   # or: python3 -m venv .venv-vmtool && .venv-vmtool/bin/pip install vm-tool

Env (do not commit secrets):
  EC2_HOST              public IP or DNS
  EC2_USER              ubuntu | ec2-user | ...
  EC2_SSH_KEY           path to .pem (preferred)
  EC2_SSH_PASSWORD      password auth if no key (optional)
  GITHUB_USERNAME       e.g. Ashish4895
  GITHUB_TOKEN          optional; needed only if repo is private
  GITHUB_PROJECT_URL    default https://github.com/Ashish4895/pensieve
  GITHUB_BRANCH         default main
  DOCKERHUB_USERNAME    optional
  DOCKERHUB_PASSWORD    optional

After clone+compose on the host, ensure a .env exists on the EC2 project
with DJANGO_SECRET_KEY and GEMINI_API_KEY (compose requires the secret key).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    try:
        from vm_tool.runner import SetupRunner, SetupRunnerConfig, SSHConfig
    except ImportError:
        print("vm_tool not installed. Run: pip install vm-tool", file=sys.stderr)
        return 1

    host = os.environ.get("EC2_HOST", "").strip()
    user = os.environ.get("EC2_USER", "").strip()
    key = os.environ.get("EC2_SSH_KEY", "").strip()
    password = os.environ.get("EC2_SSH_PASSWORD", "").strip()
    if not host or not user:
        print("Set EC2_HOST and EC2_USER", file=sys.stderr)
        return 1
    if not key and not password:
        print("Set EC2_SSH_KEY (preferred) or EC2_SSH_PASSWORD", file=sys.stderr)
        return 1
    if key and not Path(key).expanduser().is_file():
        print(f"SSH key not found: {key}", file=sys.stderr)
        return 1

    gh_user = os.environ.get("GITHUB_USERNAME", "Ashish4895").strip()
    gh_token = os.environ.get("GITHUB_TOKEN", "").strip() or "unused"
    project = os.environ.get(
        "GITHUB_PROJECT_URL", "https://github.com/Ashish4895/pensieve"
    ).strip()
    branch = os.environ.get("GITHUB_BRANCH", "main").strip()
    compose = os.environ.get("DOCKER_COMPOSE_FILE", "docker-compose.yml").strip()

    config = SetupRunnerConfig(
        github_username=gh_user,
        github_token=gh_token,
        github_project_url=project,
        github_branch=branch,
        docker_compose_file_path=compose,
        dockerhub_username=os.environ.get("DOCKERHUB_USERNAME", "") or "unused",
        dockerhub_password=os.environ.get("DOCKERHUB_PASSWORD", "") or "unused",
    )
    runner = SetupRunner(config)
    ssh = SSHConfig(
        ssh_username=user,
        ssh_password=password or "unused",
        ssh_hostname=host,
        ssh_identity_file=str(Path(key).expanduser()) if key else "",
    )
    print(f"Deploying {project}@{branch} → {user}@{host} via vm_tool …")
    runner.run_cloud_setup([ssh])
    print("vm_tool cloud setup finished.")
    print(f"Open security group for TCP 8080 (nginx) and check http://{host}:8080")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
