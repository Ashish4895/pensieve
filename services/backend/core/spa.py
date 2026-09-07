from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.views import View


def spa_root() -> Path | None:
    raw = getattr(settings, "SPA_ROOT", "") or ""
    root = Path(raw)
    if not root.is_dir() or not (root / "index.html").is_file():
        return None
    return root.resolve()


class SpaView(View):
    """Serve Vite build assets, falling back to index.html for client routes."""

    def get(self, request, path=""):
        root = spa_root()
        if root is None:
            raise Http404("SPA not packaged")

        # Normalize and reject path escape
        relative = Path(path)
        if relative.is_absolute() or ".." in relative.parts:
            raise Http404()

        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise Http404() from exc

        if path and candidate.is_file():
            return FileResponse(candidate.open("rb"))

        return FileResponse(
            (root / "index.html").open("rb"),
            content_type="text/html; charset=utf-8",
        )
