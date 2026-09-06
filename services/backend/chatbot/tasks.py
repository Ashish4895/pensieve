from celery import shared_task

from chatbot.services.ingest import ingest_documents


@shared_task(name="chatbot.run_ingest")
def run_ingest(directory: str = "documents", user_id: int | None = None) -> dict:
    result = ingest_documents(directory)
    if user_id is not None:
        from django.contrib.auth import get_user_model

        from notifications.services import create_notification

        user = get_user_model().objects.filter(pk=user_id).first()
        if user:
            create_notification(
                user=user,
                title="Ingest complete",
                body=f"files={result['files']} chunks={result['chunks']}",
                kind="ingest",
            )
    return result
