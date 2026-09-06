from django.urls import path

from chatbot.api_views import IngestEnqueueView

urlpatterns = [
    path("ingest/", IngestEnqueueView.as_view(), name="ingest-enqueue"),
]
