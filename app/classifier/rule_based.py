import re
import math
from typing import List
from app.models import ChatMessage
from .base import BaseClassifier
from .types import ClassificationResult, ModelTier


class RuleBasedClassifier(BaseClassifier):
    """
    Production-grade heuristic classifier with three-tier routing (cheap/medium/frontier).
    Uses multi-signal analysis: lexical patterns, structural cues, semantic complexity,
    conversation depth, and length to produce a continuous complexity score.
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
        r"\bpython (function|script|code|class)\b",
        r"\bpostgresql|sql query|recursive cte\b",
        r"\balgorithm\b",
        r"\bo\([n1k\^log ]+\)",
        r"\bfastapi|django|celery|redis\b",
        r"\bsolidity|smart contract\b",
        r"\btype hints?\b",
        r"\brust\b.{0,30}\b(impl|struct|trait|fn)\b",
        r"\bgo\b.{0,30}\b(goroutine|channel|interface)\b",
        r"\btypescript\b",
        r"\breact\b.{0,20}\b(component|hook|state|props)\b",
        r"\bwebpack|vite|rollup|esbuild\b",
        r"\bci/cd|github actions|pipeline\b",
    ]

    COMPLEX_REASONING_KEYWORDS = [
        "derive", "derivation", "prove", "proof", "theorem", "differential equation",
        "system design", "architecture", "trade-off", "tradeoffs",
        "concurrency", "distributed system", "distributed consensus", "byzantine",
        "optimization problem", "p vs np", "asymptotic complexity",
        "microservices vs monolith", "zero-day", "security audit", "vulnerability",
        "reentrancy", "refactor", "debug this", "memory leak", "domain-driven",
        "formal verification", "category theory", "abstract algebra",
        "neural network architecture", "transformer model", "gradient descent",
        "database schema design", "consistency model", "eventual consistency",
        "cap theorem", "raft consensus", "paxos", "crdt",
        "compiler design", "lexer", "parser", "abstract syntax tree",
        "machine learning pipeline", "feature engineering", "hyperparameter",
    ]

    MEDIUM_REASONING_KEYWORDS = [
        "explain", "compare", "analyze", "summarize", "write a",
        "create a", "build a", "implement", "design a",
        "review this", "improve this", "convert this",
        "how does", "why does", "what are the", "pros and cons",
        "best practices", "step by step", "tutorial",
        "format as", "markdown", "table", "list",
        "data analysis", "visualization", "chart",
        "api", "endpoint", "rest", "graphql",
        "unit test", "integration test",
    ]

    SIMPLE_PATTERNS = [
        r"^(hi|hello|hey|bonjour|salut|coucou|good morning|good evening)[\s!.]*$",
        r"^\s*(thanks|thank you|merci|ok|okay|sure|yes|no|oui|non)\s*[!.]*\s*$",
        r"\bcapital of\b",
        r"\btranslate (to|into|in)\b",
        r"\btraduis (en|vers)\b",
        r"\bdefine\b",
        r"^what is .{3,30}\??\s*$",
        r"\bqui est\b",
        r"\bc'est quoi\b",
        r"\bcheck spelling\b",
        r"\bcorrige l'orthographe\b",
        r"^(who|what|when|where) (is|was|are|were) .{3,40}\??\s*$",
    ]

    CREATIVE_KEYWORDS = [
        "poem", "poetry", "story", "short story", "novel", "narrative",
        "joke", "humor", "imagine", "creative", "fictional",
        "blog post", "essay", "article", "letter", "email draft",
        "song", "lyrics", "screenplay", "dialogue", "monologue",
        "rpg", "roleplay", "character", "world-building",
    ]

    def __init__(self, threshold: float = 0.50):
        self.threshold = threshold
        self.code_regexes = [re.compile(p, re.IGNORECASE) for p in self.CODE_PATTERNS]
        self.simple_regexes = [re.compile(p, re.IGNORECASE) for p in self.SIMPLE_PATTERNS]
        # Thresholds for three tiers
        self.cheap_ceiling = 0.35
        self.frontier_floor = 0.65

    @staticmethod
    def _calculate_probabilities(score: float) -> dict[str, float]:
        # Smooth gaussian bell curves centered at 0.10 (cheap), 0.50 (medium), 0.88 (frontier)
        w_cheap = math.exp(-((score - 0.10) / 0.28) ** 2)
        w_medium = math.exp(-((score - 0.50) / 0.25) ** 2)
        w_frontier = math.exp(-((score - 0.88) / 0.28) ** 2)
        total = w_cheap + w_medium + w_frontier
        return {
            "cheap": round(w_cheap / total, 4),
            "medium": round(w_medium / total, 4),
            "frontier": round(w_frontier / total, 4),
        }

    def classify(self, messages: List[ChatMessage]) -> ClassificationResult:
        if not messages:
            return ClassificationResult(
                tier=ModelTier.CHEAP,
                confidence=0.9,
                score=0.1,
                reasons=["Empty message context routed to cheap tier by default"],
                suggested_model="cheap",
                probabilities={"cheap": 0.85, "medium": 0.12, "frontier": 0.03}
            )

        # Aggregate text from recent messages, focusing on the latest user message
        user_messages = [m.content for m in messages if m.role == "user"]
        latest_user_text = user_messages[-1] if user_messages else messages[-1].content
        full_text = "\n".join([m.content for m in messages])

        reasons: List[str] = []
        score = 0.18  # Baseline neutral prior (slight lean toward cheap)

        # 1. Simple heuristic shortcut — strong cheap signal
        for s_reg in self.simple_regexes:
            if s_reg.search(latest_user_text.strip()):
                reasons.append("Matches simple conversational/factual intent pattern")
                score -= 0.15
                break

        # 2. Code detection — strong complexity signal
        code_matches = sum(1 for reg in self.code_regexes if reg.search(full_text))
        if code_matches > 0:
            boost = min(0.55, 0.30 + (code_matches - 1) * 0.08)
            score += boost
            reasons.append(f"Detected programming syntax or code snippets ({code_matches} pattern matches)")

        # 3. High reasoning / technical keywords — strong frontier signal
        text_lower = full_text.lower()
        keyword_hits = [kw for kw in self.COMPLEX_REASONING_KEYWORDS if kw in text_lower]
        if keyword_hits:
            boost = min(0.60, 0.30 + (len(keyword_hits) - 1) * 0.10)
            score += boost
            reasons.append(f"Contains complex reasoning / architecture concepts: {', '.join(keyword_hits[:3])}")

        # 4. Medium-level keywords — moderate complexity signal
        medium_hits = [kw for kw in self.MEDIUM_REASONING_KEYWORDS if kw in text_lower]
        if medium_hits and not keyword_hits:  # Only apply if no heavy reasoning detected
            boost = min(0.30, 0.12 + (len(medium_hits) - 1) * 0.06)
            score += boost
            reasons.append(f"Contains structured task indicators: {', '.join(medium_hits[:3])}")

        # 5. Creative keywords — moderate complexity
        creative_hits = [kw for kw in self.CREATIVE_KEYWORDS if kw in text_lower]
        if creative_hits:
            boost = min(0.25, 0.10 + (len(creative_hits) - 1) * 0.06)
            score += boost
            reasons.append(f"Creative writing/generation task: {', '.join(creative_hits[:3])}")

        # 6. Context length & multi-turn complexity
        total_length = len(full_text)
        if total_length > 2000:
            score += 0.30
            reasons.append(f"Very extensive context length ({total_length} characters)")
        elif total_length > 1200:
            score += 0.22
            reasons.append(f"Extensive context length ({total_length} characters)")
        elif total_length > 500:
            score += 0.12
            reasons.append(f"Moderate context length ({total_length} characters)")

        if len(messages) >= 6:
            score += 0.15
            reasons.append(f"Deep multi-turn conversation ({len(messages)} turns)")
        elif len(messages) >= 4:
            score += 0.08
            reasons.append(f"Multi-turn conversation history ({len(messages)} turns)")

        # 7. Question complexity (number of questions, conditionals)
        question_count = text_lower.count("?")
        if question_count >= 3:
            score += 0.10
            reasons.append(f"Multiple questions detected ({question_count} questions)")

        conditional_keywords = ["if", "but", "however", "unless", "although", "whereas"]
        cond_count = sum(1 for kw in conditional_keywords if f" {kw} " in f" {text_lower} ")
        if cond_count >= 3:
            score += 0.08
            reasons.append(f"Complex conditional reasoning ({cond_count} qualifiers)")

        # Normalize score between 0.0 and 1.0
        score = max(0.0, min(1.0, score))

        # Three-tier routing
        if score >= self.frontier_floor:
            tier = ModelTier.FRONTIER
        elif score >= self.cheap_ceiling:
            tier = ModelTier.MEDIUM
        else:
            tier = ModelTier.CHEAP

        # Confidence: distance from nearest boundary
        if tier == ModelTier.FRONTIER:
            boundary_dist = score - self.frontier_floor
        elif tier == ModelTier.CHEAP:
            boundary_dist = self.cheap_ceiling - score
        else:
            boundary_dist = min(score - self.cheap_ceiling, self.frontier_floor - score)

        confidence = max(0.55, min(0.99, 0.60 + boundary_dist))

        if not reasons:
            if tier == ModelTier.FRONTIER:
                reasons.append("High complexity detected across heuristics — frontier model recommended")
            elif tier == ModelTier.MEDIUM:
                reasons.append("Moderate complexity — mid-tier model offers best value")
            else:
                reasons.append("Low complexity: routine query suitable for lightweight/local LLM")

        probs = self._calculate_probabilities(score)

        return ClassificationResult(
            tier=tier,
            confidence=round(confidence, 2),
            score=round(score, 3),
            reasons=reasons,
            suggested_model=tier.value,
            probabilities=probs,
            metadata={
                "message_count": len(messages),
                "total_chars": total_length,
                "score_threshold_cheap": self.cheap_ceiling,
                "score_threshold_frontier": self.frontier_floor,
            }
        )
