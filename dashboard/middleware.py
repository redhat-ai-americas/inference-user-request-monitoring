import json
import sys
from typing import Callable

class OpenAITokenLoggerMiddleware:
    def __init__(self, app: Callable) -> None:
        self.app = app
    
    def print_log(self,
                  user: str,
                  request: str,
                  response: str,
                  request_id: str = "unknown",
                  model: str = "unknown",
                  prompt_tokens: int = 0,
                  completion_tokens: int = 0,
                  total_tokens: int = 0,
                 ):
        print(f"[OpenAI Usage] "
              f"Request ID: {request_id}, "
              f"Model: {model}, "
              f"User: {user}, "
              f"Prompt: {prompt_tokens}, "
              f"Completion: {completion_tokens}, "
              f"Total: {total_tokens}, "
              f"Request: {request}, "
              f"Response: {response}",
              file=sys.stdout)
        sys.stdout.flush()

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        detail_dict = {
            "user": dict(scope["headers"]).get(b"x-forwarded-user", b"").decode("utf-8")
        }

        request_body = b""
        async def receive_wrapper():
            nonlocal request_body
            nonlocal detail_dict
            message = await receive()
            if message.get("type", "") == "http.disconnect":
                if 'state' in scope and 'request_metadata' in scope['state']:
                    final_usage_info = scope['state']['request_metadata'].final_usage_info
                    detail_dict["prompt_tokens"] = final_usage_info.prompt_tokens
                    detail_dict["completion_tokens"] = final_usage_info.completion_tokens
                    detail_dict["total_tokens"] = final_usage_info.total_tokens
                self.print_log(**detail_dict)

                return message
            request_body = message['body']
            detail_dict['request'] = message['body'].decode('utf-8', errors='ignore')
            return message
        
        response_body = b""
        is_streaming = False

        def parse_sse_chunk(chunk_text: str):
            """Parse a single SSE chunk and extract JSON data"""
            lines = chunk_text.strip().split('\n')
            for line in lines:
                if line.startswith('data: '):
                    data_part = line[6:]  # Remove 'data: ' prefix
                    if data_part.strip() == '[DONE]':
                        return None
                    try:
                        return json.loads(data_part)
                    except json.JSONDecodeError:
                        continue
            return None

        def is_sse_response(headers):
            """Check if response is Server-Sent Events"""
            for name, value in headers:
                if name == b'content-type' and b'text/event-stream' in value:
                    return True
            return False

        async def send_wrapper(message):
            nonlocal response_body, is_streaming, detail_dict

            if message["type"] == "http.response.start":
                # Check if this is a streaming response
                is_streaming = is_sse_response(message.get("headers", []))
                
            elif message["type"] == "http.response.body":
                body = message.get("body", b"")
                response_body += body

                if is_streaming:
                    # Process streaming chunks as they arrive
                    try:
                        parsed_data = parse_sse_chunk(body.decode("utf-8"))
                        
                        if parsed_data:
                            # Store stream metadata from first chunk
                            if detail_dict.get('request_id', None) is None:
                                detail_dict['request_id'] = parsed_data.get('id', 'unknown')
                                detail_dict['model'] = parsed_data.get('model', 'unknown')

                            # Accumulate content from delta chunks
                            if "choices" in parsed_data and parsed_data["choices"]:
                                delta = parsed_data["choices"][0].get("delta", {})
                                if "content" in delta:
                                    if 'response' not in detail_dict:
                                        detail_dict['response'] = ''
                                    detail_dict['response'] += delta["content"]
                        
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        pass

                # If this is the last chunk (more_body is False)
                if not message.get("more_body", False):
                    if not is_streaming:
                        # Handle regular JSON responses (existing logic)
                        try:
                            data = json.loads(response_body.decode("utf-8"))
                            if "usage" in data:
                                usage = data["usage"]

                                detail_dict['response'] = data.get('choices', [{}])[0].get('message', {}).get('content', '') if 'choices' in data else ''
                                detail_dict['request_id'] = data.get('id', 'unknown')
                                detail_dict['model'] = data.get('model', 'unknown')
                                detail_dict['prompt_tokens'] = usage.get('prompt_tokens', 0)
                                detail_dict['completion_tokens'] = usage.get('completion_tokens', 0)
                                detail_dict['total_tokens'] = usage.get('total_tokens', 0)
                                self.print_log(**detail_dict)
                        except (json.JSONDecodeError, UnicodeDecodeError, KeyError, IndexError):
                            pass

            await send(message)

        await self.app(scope, receive_wrapper, send_wrapper)
