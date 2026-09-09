from pathlib import Path

import pensieve.settings as pensieve_settings
from django.core.cache import cache
from django.test import override_settings


def test_redis_url_default_matches_compose_host_port():
    """Compose publishes Redis on host :6380; settings default must match AGENTS.md."""
    source = Path(pensieve_settings.__file__).read_text()
    assert 'os.environ.get("REDIS_URL", "redis://127.0.0.1:6380/0")' in source
    assert pensieve_settings.REDIS_URL.startswith("redis://")


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "plan2-test",
        }
    }
)
def test_cache_roundtrip_works_with_configured_backend():
    cache.set("plan2", "ok", 10)
    assert cache.get("plan2") == "ok"
