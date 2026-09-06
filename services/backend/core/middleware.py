import uuid


class RequestIdMiddleware:
    header_name = "X-Request-ID"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.META.get("HTTP_X_REQUEST_ID", "").strip()
        if not request_id:
            request_id = str(uuid.uuid4())
        request.request_id = request_id

        response = self.get_response(request)
        response[self.header_name] = request_id
        return response
