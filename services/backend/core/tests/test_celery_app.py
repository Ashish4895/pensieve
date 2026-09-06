def test_celery_app_loads_django_settings():
    from pensieve.celery import app

    assert app.main.endswith("pensieve") or app.main == "pensieve"
    assert app.conf.task_serializer == "json"
