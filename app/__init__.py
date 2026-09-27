"""LLM-Router: Intelligent OpenAI-compatible LLM Gateway."""
import os

# Clean bracketed IPv6 in NO_PROXY/no_proxy to prevent httpx InvalidURL error
for _var in ("NO_PROXY", "no_proxy"):
    _val = os.environ.get(_var)
    if _val and "[" in _val:
        os.environ[_var] = ",".join(
            item for item in _val.split(",") if not (item.startswith("[") and item.endswith("]"))
        )

__version__ = "0.1.0"

