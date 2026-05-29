class WebhookDebugMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/webhooks/"):
            print("🔥 WEBHOOK HIT")
            print("PATH:", request.path)
            print("METHOD:", request.method)
            print("HEADERS:", dict(request.headers))
        return self.get_response(request)
