import json
import sys
from typing import Callable


class OpenAITokenLoggerMiddleware:
    def __init__(self, app: Callable) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_body = b""
        async def receive_wrapper():
            nonlocal request_body
            message = await receive()
            request_body = message['body']
            return message


        # byte buffer for response
        user = dict(scope["headers"]).get(b"x-forwarded-user", b"").decode("utf-8")
        response_body = b""
        
        async def send_wrapper(message):
            nonlocal response_body
            
            if message["type"] == "http.response.body":
                body = message.get("body", b"")
                response_body += body
            
                # If this is the last chunk (more_body is False)
                if not message.get("more_body", False):
                    try:
                        # Try to parse as JSON
                        data = json.loads(response_body.decode("utf-8"))
                        if "usage" in data:
                            usage = data["usage"]
                            print(f"[OpenAI Usage] "
                                  f"Request ID: {data.get('id', 0)}, "
                                  f"Model: {data.get('model', '')}, "
                                  f"User: {user}, "
                                  f"Prompt: {usage.get('prompt_tokens', 0)}, "
                                  f"Completion: {usage.get('completion_tokens', 0)}, "
                                  f"Total: {usage.get('total_tokens', 0)}, ", 
                                  f"Request: {request_body.decode("utf-8")}, ",
                                  f"Response: {data.get('choices')[0]['message'] if 'choices' in data else ''}",
                                  file=sys.stdout)
                            sys.stdout.flush()
                    except (json.JSONDecodeError, UnicodeDecodeError, KeyError):
                        # Not JSON or doesn't have expected structure
                        pass
            
            await send(message)

        await self.app(scope, receive_wrapper, send_wrapper)
