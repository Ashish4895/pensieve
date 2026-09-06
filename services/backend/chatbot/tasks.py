from celery import shared_task

from chatbot.services.ingest import ingest_documents


@shared_task(name="chatbot.run_ingest")
def run_ingest(directory: str = "documents") -> dict:
    return ingest_documents(directory)
