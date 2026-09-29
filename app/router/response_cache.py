"""
Semantic Response Cache — exact-match fast path + fuzzy near-match via aggressive
text normalization and textual similarity.

Strategy:
1. Exact key match (SHA-256 of canonical request fields) — O(1), zero overhead.
2. If no exact hit, normalize the prompt text aggressively (lowercase, strip
   punctuation/articles/filler, collapse whitespace, sort words) and compare
   against cached normalized keys using SequenceMatcher ratio.
   Threshold: 0.92 (configurable).  This catches typo fixes, rewordings, and
   near-identical prompts without any embedding model.
3. Cache entries expire after TTL seconds.

Dashboard stats: hit_count, miss_count, semantic_hit_count, savings_usd tracked.
"""

import hashlib
import json
import re
import time
import unicodedata
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

from app.models import ChatCompletionRequest, ChatCompletionResponse, RouterMetadata


# ── Aggressive text normalizer ──────────────────────────────────────────────

_ARTICLES = re.compile(r"\b(a|an|the|this|that|these|those|my|your|our|his|her|its|their)\b", re.I)
_FILLERS = re.compile(r"\b(please|kindly|just|simply|basically|actually|really|very|quite|can you|could you|would you|i want you to|i need you to|i'd like you to|help me)\b", re.I)
_PUNCT = re.compile(r"[^\w\s]", re.U)
_MULTI_WS = re.compile(r"\s+")


def _normalize_text(text: str) -> str:
    """Aggressively normalize text for semantic comparison.

    Strips accents, articles, filler words, punctuation; lowercases and
    collapses whitespace.  The result is NOT meant to be human-readable —
    it's a canonical form for similarity comparison.
    """
    # Unicode NFKD decomposition → strip combining marks (accents)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))

    text = text.lower()
    text = _ARTICLES.sub(" ", text)
    text = _FILLERS.sub(" ", text)
    text = _PUNCT.sub(" ", text)
    text = _MULTI_WS.sub(" ", text).strip()
    return text


def _similarity(a: str, b: str) -> float:
    """Fast string similarity (SequenceMatcher ratio) between two normalized texts."""
    if a == b:
        return 1.0
    # Quick length check — if lengths differ by > 40% they're unlikely similar
    if len(a) == 0 or len(b) == 0:
        return 0.0
    ratio = len(a) / len(b) if len(b) > 0 else 0.0
    if ratio < 0.6 or ratio > 1.67:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


# ── Cache entry ─────────────────────────────────────────────────────────────

class _CacheEntry:
    __slots__ = ("timestamp", "response", "normalized_prompt", "exact_key", "cost_usd", "params_sig")

    def __init__(
        self,
        timestamp: float,
        response: ChatCompletionResponse,
        normalized_prompt: str,
        exact_key: str,
        cost_usd: float,
        params_sig: str = "",
    ):
        self.timestamp = timestamp
        self.response = response
        self.normalized_prompt = normalized_prompt
        self.exact_key = exact_key
        self.cost_usd = cost_usd
        self.params_sig = params_sig


# ── ResponseCache ───────────────────────────────────────────────────────────

class ResponseCache:
    """In-memory response cache with exact-match + semantic near-match."""

    def __init__(self, ttl_seconds: int = 3600, similarity_threshold: float = 0.92):
        self.ttl_seconds = ttl_seconds
        self.similarity_threshold = similarity_threshold

        # Primary index: exact SHA → entry
        self._exact: Dict[str, _CacheEntry] = {}
        # Secondary list for semantic scan (kept small via TTL eviction)
        self._entries: List[_CacheEntry] = []

        # Stats
        self.hit_count: int = 0
        self.miss_count: int = 0
        self.semantic_hit_count: int = 0
        self.savings_usd: float = 0.0

    # ── Key generation ──────────────────────────────────────────────────

    @staticmethod
    def _generate_key(request: ChatCompletionRequest) -> str:
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

    @staticmethod
    def _extract_prompt_text(request: ChatCompletionRequest) -> str:
        """Extract the user-visible prompt text for semantic comparison."""
        parts = []
        for m in request.messages:
            if m.role in ("user", "system"):
                parts.append(m.content)
        return " ".join(parts)

    @staticmethod
    def _params_signature(request: ChatCompletionRequest) -> str:
        """Signature of non-prompt parameters that affect output (model, temperature, etc.)."""
        return f"{request.model}|{request.temperature}|{request.top_p}|{request.max_tokens}|{request.strategy}"

    # ── Eviction ────────────────────────────────────────────────────────

    def _evict_expired(self) -> None:
        now = time.time()
        expired_keys = []
        alive = []
        for entry in self._entries:
            if now - entry.timestamp >= self.ttl_seconds:
                expired_keys.append(entry.exact_key)
            else:
                alive.append(entry)
        self._entries = alive
        for k in expired_keys:
            self._exact.pop(k, None)

    # ── Lookup ──────────────────────────────────────────────────────────

    def get(self, request: ChatCompletionRequest) -> Optional[ChatCompletionResponse]:
        self._evict_expired()

        exact_key = self._generate_key(request)

        # 1) Exact match
        entry = self._exact.get(exact_key)
        if entry and time.time() - entry.timestamp < self.ttl_seconds:
            self.hit_count += 1
            self.savings_usd += entry.cost_usd
            cached = entry.response.model_copy(deep=True)
            return cached

        # 2) Semantic near-match
        prompt_text = self._extract_prompt_text(request)
        norm = _normalize_text(prompt_text)
        if not norm:
            self.miss_count += 1
            return None

        req_sig = self._params_signature(request)
        best_score = 0.0
        best_entry: Optional[_CacheEntry] = None
        for e in self._entries:
            # Only consider entries with matching non-prompt parameters
            if e.params_sig != req_sig:
                continue
            sim = _similarity(norm, e.normalized_prompt)
            if sim > best_score:
                best_score = sim
                best_entry = e

        if best_score >= self.similarity_threshold and best_entry is not None:
            self.hit_count += 1
            self.semantic_hit_count += 1
            self.savings_usd += best_entry.cost_usd
            cached = best_entry.response.model_copy(deep=True)
            return cached

        self.miss_count += 1
        return None

    # ── Store ───────────────────────────────────────────────────────────

    def set(self, request: ChatCompletionRequest, response: ChatCompletionResponse) -> None:
        exact_key = self._generate_key(request)
        prompt_text = self._extract_prompt_text(request)
        norm = _normalize_text(prompt_text)
        cost = 0.0
        if hasattr(response, "router_metadata") and response.router_metadata:
            cost = response.router_metadata.cost_actual_usd or 0.0

        entry = _CacheEntry(
            timestamp=time.time(),
            response=response,
            normalized_prompt=norm,
            exact_key=exact_key,
            cost_usd=cost,
            params_sig=self._params_signature(request),
        )
        self._exact[exact_key] = entry
        self._entries.append(entry)

        # Cap total entries to prevent unbounded memory growth
        if len(self._entries) > 500:
            # Remove oldest half
            self._entries.sort(key=lambda e: e.timestamp)
            removed = self._entries[: len(self._entries) // 2]
            self._entries = self._entries[len(self._entries) // 2 :]
            for r in removed:
                self._exact.pop(r.exact_key, None)

    # ── Stats ───────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        total = self.hit_count + self.miss_count
        return {
            "total_entries": len(self._entries),
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "semantic_hit_count": self.semantic_hit_count,
            "hit_rate": round(self.hit_count / total, 4) if total > 0 else 0.0,
            "savings_usd": round(self.savings_usd, 6),
        }

    # ── Clear ───────────────────────────────────────────────────────────

    def clear(self) -> None:
        self._exact.clear()
        self._entries.clear()
        # Don't reset stats — they're cumulative


global_response_cache = ResponseCache()
