from rest_framework.permissions import IsAuthenticated
from rest_framework.status import HTTP_202_ACCEPTED
from rest_framework.views import APIView

from chatbot.tasks import run_ingest
from core.api import api_success


class IngestEnqueueView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        directory = request.data.get("directory") or "documents"
        if not isinstance(directory, str) or not directory.strip():
            directory = "documents"

        async_result = run_ingest.delay(directory.strip())
        return api_success(
            data={"task_id": async_result.id},
            message="Ingest enqueued",
            status_code=HTTP_202_ACCEPTED,
        )
