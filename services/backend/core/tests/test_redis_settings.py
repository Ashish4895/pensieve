from django.conf import settings
from django.core.cache import cache
from django.test import override_settings


def test_redis_url_default_matches_compose_host_port():
    assert settings.REDIS_URL == "redis://127.0.0.1:6380/0"


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
