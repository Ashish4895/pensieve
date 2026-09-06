import pytest
from django.core.management import call_command
from django.test import override_settings
from io import StringIO


@override_settings(DEBUG=False)
def test_reload_celery_refuses_when_not_debug():
    err = StringIO()
    with pytest.raises(SystemExit) as exc:
        call_command("reload_celery", stderr=err)
    assert exc.value.code != 0
    assert "reload_celery is only allowed when DEBUG=true" in err.getvalue()
