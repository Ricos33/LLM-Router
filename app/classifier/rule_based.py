import re
from typing import List
from app.models import ChatMessage
from .base import BaseClassifier
from .types import ClassificationResult, ModelTier


class RuleBasedClassifier(BaseClassifier):
    """
    Explainable rule-based mock classifier.
    Routes queries to 'cheap' (local / small models) or 'frontier' (GPT-4o, Claude 3.5)
    based on syntactic, semantic, and complexity heuristics.
    """

    CODE_PATTERNS = [
        r"```",
        r"\bdef\s+\w+\s*\(",
        r"\bclass\s+\w+[\(:]",
        r"\bimport\s+\w+",
        r"\bfrom\s+\w+\s+import",
        r"\bfunction\b",
        r"\bSELECT\s+.+\s+FROM\b",
        r"\bINSERT\s+INTO\b",
        r"\bUPDATE\s+.+\s+SET\b",
        r"\bcurl\s+-",
        r"\bdockerfile\b",
        r"\bkubernetes\b",
        r"\basync\s+def\b",
        r"\bregex\b",
        r"\bpython (function|script|code|class)\b",
        r"\bpostgresql|sql query|recursive cte\b",
        r"\balgorithm\b",
        r"\bo\([n1k\^log ]+\)",
        r"\bfastapi|django|celery|redis\b",
        r"\bsolidity|smart contract\b",
        r"\btype hints\b"
    ]

    COMPLEX_REASONING_KEYWORDS = [
        "derive", "derivation", "prove", "proof", "theorem", "differential equation",
        "system design", "architecture", "trade-off", "tradeoffs",
        "concurrency", "distributed system", "distributed consensus", "byzantine",
        "optimization problem", "p vs np", "asymptotic complexity",
        "microservices vs monolith", "zero-day", "security audit", "vulnerability", "reentrancy",
        "refactor", "debug this", "memory leak", "domain-driven"
    ]

    SIMPLE_PATTERNS = [
        r"^(hi|hello|hey|bonjour|salut|coucou|good morning)[\s!.]*$",
        r"\bcapital of\b",
        r"\btranslate (to|into|in)\b",
        r"\btraduis (en|vers)\b",
        r"\bdefine\b",
        r"\bwhat is\b",
        r"\bqui est\b",
        r"\bc'est quoi\b",
        r"\bcheck spelling\b",
        r"\bcorrige l'orthographe\b"
    ]

    def __init__(self, threshold: float = 0.50):
        self.threshold = threshold
        self.code_regexes = [re.compile(p, re.IGNORECASE) for p in self.CODE_PATTERNS]
        self.simple_regexes = [re.compile(p, re.IGNORECASE) for p in self.SIMPLE_PATTERNS]

    def classify(self, messages: List[ChatMessage]) -> ClassificationResult:
        if not messages:
            return ClassificationResult(
                tier=ModelTier.CHEAP,
                confidence=0.9,
                score=0.1,
                reasons=["Empty message context routed to cheap tier by default"],
                suggested_model="cheap"
            )

        # Aggregate text from recent messages, focusing on the latest user message
        user_messages = [m.content for m in messages if m.role == "user"]
        latest_user_text = user_messages[-1] if user_messages else messages[-1].content
        full_text = "\n".join([m.content for m in messages])

        reasons: List[str] = []
        score = 0.20  # Baseline neutral prior (slight lean to cheap)

        # 1. Simple heuristic shortcut
        for s_reg in self.simple_regexes:
            if s_reg.search(latest_user_text.strip()):
                reasons.append("Matches simple conversational/factual intent pattern")
                score -= 0.15
                break

        # 2. Code detection
        code_matches = sum(1 for reg in self.code_regexes if reg.search(full_text))
        if code_matches > 0:
            boost = min(0.55, 0.35 + (code_matches - 1) * 0.10)
            score += boost
            reasons.append(f"Detected programming syntax or code snippets ({code_matches} pattern matches)")

        # 3. High reasoning / technical keywords
        text_lower = full_text.lower()
        keyword_hits = [kw for kw in self.COMPLEX_REASONING_KEYWORDS if kw in text_lower]
        if keyword_hits:
            boost = min(0.60, 0.35 + (len(keyword_hits) - 1) * 0.12)
            score += boost
            reasons.append(f"Contains complex reasoning / architecture concepts: {', '.join(keyword_hits[:3])}")

        # 4. Context length & multi-turn complexity
        total_length = len(full_text)
        if total_length > 1200:
            score += 0.25
            reasons.append(f"Extensive context length ({total_length} characters)")
        elif total_length > 500:
            score += 0.15
            reasons.append(f"Moderate context length ({total_length} characters)")

        if len(messages) >= 4:
            score += 0.10
            reasons.append(f"Multi-turn conversation history ({len(messages)} turns)")

        # Normalize score between 0.0 and 1.0
        score = max(0.0, min(1.0, score))

        tier = ModelTier.FRONTIER if score >= self.threshold else ModelTier.CHEAP
        confidence = round(abs(score - self.threshold) * 2.0, 2)
        confidence = max(0.55, min(0.99, 0.50 + confidence / 2))

        if not reasons:
            if tier == ModelTier.FRONTIER:
                reasons.append("Moderate complexity detected across heuristics")
            else:
                reasons.append("Low complexity: routine query suitable for lightweight/local LLM")

        return ClassificationResult(
            tier=tier,
            confidence=round(confidence, 2),
            score=round(score, 3),
            reasons=reasons,
            suggested_model=tier.value,
            metadata={
                "message_count": len(messages),
                "total_chars": total_length,
                "score_threshold": self.threshold
            }
        )
