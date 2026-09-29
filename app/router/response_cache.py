import hashlib
import json
import time
from typing import Dict, Optional, Tuple
from app.models import ChatCompletionRequest, ChatCompletionResponse, RouterMetadata

class ResponseCache:
    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Tuple[float, ChatCompletionResponse]] = {}

    def _generate_key(self, request: ChatCompletionRequest) -> str:
        # Include all relevant fields that change the output
        msgs_dict = [msg.model_dump() for msg in request.messages]
        data = {
            "model": request.model,
            "messages": msgs_dict,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "max_tokens": request.max_tokens,
            "strategy": request.strategy,
        }
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode("utf-8")).hexdigest()

    def get(self, request: ChatCompletionRequest) -> Optional[ChatCompletionResponse]:
        key = self._generate_key(request)
        if key in self.cache:
            timestamp, response = self.cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                # Return a copy to avoid mutating the cached object's metadata
                cached_response = response.model_copy(deep=True)
                return cached_response
            else:
                del self.cache[key]
        return None

    def set(self, request: ChatCompletionRequest, response: ChatCompletionResponse):
        key = self._generate_key(request)
        self.cache[key] = (time.time(), response)

    def clear(self):
        self.cache.clear()

global_response_cache = ResponseCache()
