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
        "optimization problem", "p vs np", "p=np", "p = np", "asymptotic complexity",
        "np-complete", "np-hard", "godel", "undecidable", "halting problem", "formal proof",
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

    def analyze_category_scores(self, full_text: str) -> dict[str, float]:
        text_lower = full_text.lower()

        # 1. Coding score
        code_matches = sum(1 for reg in self.code_regexes if reg.search(full_text))
        coding_keywords = ["code", "script", "debug", "error", "refactor", "algorithm", "function", "variable", "api", "syntax", "pass", "return"]
        code_kw_hits = sum(1 for kw in coding_keywords if kw in text_lower)
        coding_score = min(1.0, (code_matches * 0.45) + (code_kw_hits * 0.15))

        # 2. Reasoning score
        reasoning_hits = sum(1 for kw in self.COMPLEX_REASONING_KEYWORDS if kw in text_lower)
        medium_hits = sum(1 for kw in self.MEDIUM_REASONING_KEYWORDS if kw in text_lower)
        q_count = text_lower.count("?")
        reasoning_score = min(1.0, 0.12 + (reasoning_hits * 0.28) + (medium_hits * 0.08) + min(0.12, q_count * 0.04))

        # 3. Summary score
        summary_keywords = ["summarize", "summary", "tldr", "tl;dr", "bullet points", "key takeaways", "condense", "briefly", "shorten", "overview", "recap"]
        sum_hits = sum(1 for kw in summary_keywords if kw in text_lower)
        summary_score = min(1.0, sum_hits * 0.35)

        # 4. Creative score
        creative_hits = sum(1 for kw in self.CREATIVE_KEYWORDS if kw in text_lower)
        creative_score = min(1.0, creative_hits * 0.30)

        # Baseline normalization: if everything is very low, give baseline conversational reasoning
        if max(coding_score, reasoning_score, summary_score, creative_score) < 0.25:
            reasoning_score = 0.18

        return {
            "Reasoning": round(max(0.05, min(1.0, reasoning_score)), 2),
            "Coding": round(max(0.0, min(1.0, coding_score)), 2),
            "Summary": round(max(0.0, min(1.0, summary_score)), 2),
            "Creative": round(max(0.0, min(1.0, creative_score)), 2),
        }

    def detect_domain_intent(self, full_text: str, category_scores: dict[str, float]) -> tuple[str, list[str]]:
        text_lower = full_text.lower()
        tags = []

        is_arch = any(k in text_lower for k in ["distributed system", "microservice", "architecture", "consensus", "byzantine", "idempotent", "event-driven", "kafka", "ledger", "database schema"])
        is_proof = any(k in text_lower for k in ["prove", "proof", "theorem", "undecidable", "halting problem", "p vs np", "asymptotic complexity", "differential equation"])
        is_security = any(k in text_lower for k in ["security audit", "vulnerability", "zero-day", "exploit", "reentrancy", "cve", "penetration test", "injection attack"])
        is_data = any(k in text_lower for k in ["sql query", "postgresql", "cte", "index", "table scan", "data pipeline", "etl", "analytics", "dataframe", "pandas"])

        if is_proof:
            intent = "formal_reasoning"
            tags.extend(["Proof", "Reasoning"])
        elif is_security:
            intent = "security_audit"
            tags.extend(["Security", "Reasoning"])
        elif is_arch:
            intent = "system_architecture"
            tags.extend(["Architecture", "Reasoning"])
        elif category_scores.get("Coding", 0) >= 0.40:
            intent = "code_engineering"
            tags.append("Coding")
            if any(k in text_lower for k in ["debug", "error", "exception", "bug"]):
                tags.append("Debugging")
            elif any(k in text_lower for k in ["refactor", "clean", "type hints"]):
                tags.append("Refactor")
        elif is_data:
            intent = "data_engineering"
            tags.extend(["Data", "Coding"])
        elif category_scores.get("Summary", 0) >= 0.35:
            intent = "content_summary"
            tags.append("Summary")
        elif category_scores.get("Creative", 0) >= 0.35:
            intent = "creative_writing"
            tags.append("Creative")
        elif category_scores.get("Reasoning", 0) >= 0.55:
            intent = "complex_reasoning"
            tags.append("Reasoning")
        else:
            intent = "conversational"
            tags.append("Conversational")

        if len(full_text) > 1000:
            tags.append("Long")

        return intent, tags

    STRATEGY_THRESHOLDS = {
        "cost_optimized": (0.45, 0.75),
        "balanced": (0.35, 0.65),
        "quality_optimized": (0.25, 0.50),
    }

    def classify(self, messages: List[ChatMessage], strategy: str = "balanced") -> ClassificationResult:
        strat_key = strategy.lower().strip() if strategy else "balanced"
        cheap_ceiling, frontier_floor = self.STRATEGY_THRESHOLDS.get(
            strat_key, (self.cheap_ceiling, self.frontier_floor)
        )

        if not messages:
            return ClassificationResult(
                tier=ModelTier.CHEAP,
                confidence=0.9,
                score=0.1,
                reasons=["Empty message context routed to cheap tier by default"],
                suggested_model="cheap",
                probabilities={"cheap": 0.85, "medium": 0.12, "frontier": 0.03},
                category_scores={"Reasoning": 0.1, "Coding": 0.0, "Summary": 0.0, "Creative": 0.0},
                tags=["Conversational"],
                detected_intent="conversational",
                decision_trace={
                    "baseline_score": 0.10,
                    "signals": [{"signal": "Empty Context", "delta": 0.0, "detail": "Default neutral fallback"}],
                    "calculated_score": 0.10,
                    "thresholds": {"cheap_ceiling": cheap_ceiling, "frontier_floor": frontier_floor},
                    "strategy": strat_key,
                    "assigned_tier": ModelTier.CHEAP.value,
                    "detected_intent": "conversational",
                    "category_scores": {"Reasoning": 0.1, "Coding": 0.0, "Summary": 0.0, "Creative": 0.0},
                }
            )

        # Aggregate text from recent messages, focusing on the latest user message
        user_messages = [m.content for m in messages if m.role == "user"]
        latest_user_text = user_messages[-1] if user_messages else messages[-1].content
        full_text = "\n".join([m.content for m in messages])

        reasons: List[str] = []
        signals: List[dict] = []
        base_score = 0.18
        score = base_score

        # 1. Simple heuristic shortcut — strong cheap signal
        for s_reg in self.simple_regexes:
            if s_reg.search(latest_user_text.strip()):
                reasons.append("Matches simple conversational/factual intent pattern")
                signals.append({"signal": "Conversational Pattern", "delta": -0.15, "detail": "Matches routine conversational or factual greeting regex"})
                score -= 0.15
                break

        # 2. Code detection — strong complexity signal
        code_matches = sum(1 for reg in self.code_regexes if reg.search(full_text))
        if code_matches > 0:
            boost = min(0.55, 0.30 + (code_matches - 1) * 0.08)
            score += boost
            reasons.append(f"Detected programming syntax or code snippets ({code_matches} pattern matches)")
            signals.append({"signal": "Programming Syntax", "delta": round(boost, 3), "detail": f"{code_matches} code patterns matched"})

        # 3. High reasoning / technical keywords — strong frontier signal
        text_lower = full_text.lower()
        keyword_hits = [kw for kw in self.COMPLEX_REASONING_KEYWORDS if kw in text_lower]
        if keyword_hits:
            boost = min(0.60, 0.30 + (len(keyword_hits) - 1) * 0.10)
            score += boost
            reasons.append(f"Contains complex reasoning / architecture concepts: {', '.join(keyword_hits[:3])}")
            signals.append({"signal": "Formal/Architecture Concepts", "delta": round(boost, 3), "detail": f"Keywords: {', '.join(keyword_hits[:3])}"})

        # 4. Medium-level keywords — moderate complexity signal
        medium_hits = [kw for kw in self.MEDIUM_REASONING_KEYWORDS if kw in text_lower]
        if medium_hits and not keyword_hits:  # Only apply if no heavy reasoning detected
            boost = min(0.30, 0.12 + (len(medium_hits) - 1) * 0.06)
            score += boost
            reasons.append(f"Contains structured task indicators: {', '.join(medium_hits[:3])}")
            signals.append({"signal": "Structured Task Concepts", "delta": round(boost, 3), "detail": f"Keywords: {', '.join(medium_hits[:3])}"})

        # 5. Creative keywords — moderate complexity
        creative_hits = [kw for kw in self.CREATIVE_KEYWORDS if kw in text_lower]
        if creative_hits:
            boost = min(0.25, 0.10 + (len(creative_hits) - 1) * 0.06)
            score += boost
            reasons.append(f"Creative writing/generation task: {', '.join(creative_hits[:3])}")
            signals.append({"signal": "Creative Generation", "delta": round(boost, 3), "detail": f"Keywords: {', '.join(creative_hits[:3])}"})

        # 6. Context length & multi-turn complexity
        total_length = len(full_text)
        length_delta = 0.0
        if total_length > 2000:
            length_delta += 0.30
            reasons.append(f"Very extensive context length ({total_length} characters)")
        elif total_length > 1200:
            length_delta += 0.22
            reasons.append(f"Extensive context length ({total_length} characters)")
        elif total_length > 500:
            length_delta += 0.12
            reasons.append(f"Moderate context length ({total_length} characters)")

        if len(messages) >= 6:
            length_delta += 0.15
            reasons.append(f"Deep multi-turn conversation ({len(messages)} turns)")
        elif len(messages) >= 4:
            length_delta += 0.08
            reasons.append(f"Multi-turn conversation history ({len(messages)} turns)")

        if length_delta > 0:
            score += length_delta
            signals.append({"signal": "Context & Turn Depth", "delta": round(length_delta, 3), "detail": f"{total_length} chars, {len(messages)} turns"})

        # 7. Question complexity (number of questions, conditionals)
        q_delta = 0.0
        question_count = text_lower.count("?")
        if question_count >= 3:
            q_delta += 0.10
            reasons.append(f"Multiple questions detected ({question_count} questions)")

        conditional_keywords = ["if", "but", "however", "unless", "although", "whereas"]
        cond_count = sum(1 for kw in conditional_keywords if f" {kw} " in f" {text_lower} ")
        if cond_count >= 3:
            q_delta += 0.08
            reasons.append(f"Complex conditional reasoning ({cond_count} qualifiers)")

        if q_delta > 0:
            score += q_delta
            signals.append({"signal": "Question & Conditional Qualifiers", "delta": round(q_delta, 3), "detail": f"{question_count} questions, {cond_count} conditionals"})

        # Normalize score between 0.0 and 1.0
        score = max(0.0, min(1.0, score))

        # Three-tier routing
        if score >= frontier_floor:
            tier = ModelTier.FRONTIER
        elif score >= cheap_ceiling:
            tier = ModelTier.MEDIUM
        else:
            tier = ModelTier.CHEAP

        # Confidence: distance from nearest boundary
        if tier == ModelTier.FRONTIER:
            boundary_dist = score - frontier_floor
        elif tier == ModelTier.CHEAP:
            boundary_dist = cheap_ceiling - score
        else:
            boundary_dist = min(score - cheap_ceiling, frontier_floor - score)

        confidence = max(0.55, min(0.99, 0.60 + boundary_dist))

        if not reasons:
            if tier == ModelTier.FRONTIER:
                reasons.append("High complexity detected across heuristics — frontier model recommended")
            elif tier == ModelTier.MEDIUM:
                reasons.append("Moderate complexity — mid-tier model offers best value")
            else:
                reasons.append("Low complexity: routine query suitable for lightweight/local LLM")

        probs = self._calculate_probabilities(score)

        category_scores = self.analyze_category_scores(full_text)
        detected_intent, tags = self.detect_domain_intent(full_text, category_scores)

        # Append tier to tags if not present
        tier_tag = tier.value.capitalize()
        if tier_tag not in tags:
            tags.append(tier_tag)

        decision_trace = {
            "baseline_score": base_score,
            "signals": signals,
            "calculated_score": round(score, 3),
            "thresholds": {
                "cheap_ceiling": cheap_ceiling,
                "frontier_floor": frontier_floor
            },
            "strategy": strat_key,
            "assigned_tier": tier.value,
            "detected_intent": detected_intent,
            "category_scores": category_scores,
        }

        return ClassificationResult(
            tier=tier,
            confidence=round(confidence, 2),
            score=round(score, 3),
            reasons=reasons,
            suggested_model=tier.value,
            probabilities=probs,
            category_scores=category_scores,
            tags=tags,
            detected_intent=detected_intent,
            decision_trace=decision_trace,
            metadata={
                "message_count": len(messages),
                "total_chars": total_length,
                "score_threshold_cheap": self.cheap_ceiling,
                "score_threshold_frontier": self.frontier_floor,
                "detected_intent": detected_intent,
            }
        )

