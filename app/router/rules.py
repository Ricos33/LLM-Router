import re
import time
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class RoutingRule(BaseModel):
    id: str
    name: str
    description: str = ""
    enabled: bool = True
    priority: int = 100  # Higher evaluated first
    pattern: Optional[str] = None  # Regex pattern matching prompt
    keywords: Optional[List[str]] = None  # Substring keywords (OR logic)
    target_tier: Optional[str] = None  # "cheap", "medium", "frontier"
    target_model: Optional[str] = None  # Specific model ID (e.g. "anthropic/claude-sonnet-5")
    target_provider: Optional[str] = None  # Target provider
    match_count: int = 0
    created_at: float = Field(default_factory=time.time)


class RuleMatchResult(BaseModel):
    rule_id: str
    rule_name: str
    target_tier: Optional[str] = None
    target_model: Optional[str] = None
    target_provider: Optional[str] = None
    reason: str


DEFAULT_RULES: List[RoutingRule] = [
    RoutingRule(
        id="sql-database-optimization",
        name="SQL & Database Engineering",
        description="Routes deep relational database, schema migration, and complex query optimizations to Claude Sonnet 5.",
        priority=120,
        pattern=r"(?i)\b(postgresql|mysql|database\s+schema|query\s+optimization|indexing\s+strategy|sql\s+window\s+function)\b",
        keywords=["postgres", "postgresql", "sql optimization", "database migration", "acid transaction"],
        target_tier="medium",
        target_model="anthropic/claude-sonnet-5",
        target_provider="anthropic",
    ),
    RoutingRule(
        id="math-formal-proofs",
        name="Formal Math & Proofs",
        description="Routes formal mathematical proofs, topology, and advanced discrete math to GPT-6 Astra for frontier reasoning.",
        priority=115,
        pattern=r"(?i)\b(mathematical\s+induction|topology|halting\s+problem|godel|undecidable|diophantine|group\s+theory)\b",
        keywords=["mathematical induction", "formal proof", "undecidable", "turing machine", "group theory"],
        target_tier="frontier",
        target_model="openai/gpt-6-astra",
        target_provider="openai",
    ),
    RoutingRule(
        id="cybersecurity-audit",
        name="Security & Vulnerability Audit",
        description="Routes penetration testing, exploit payloads, and security audits to Claude Opus 5.5.",
        priority=110,
        pattern=r"(?i)\b(vulnerability\s+assessment|buffer\s+overflow|zero-day|xss\s+payload|sql\s+injection|penetration\s+test)\b",
        keywords=["vulnerability", "cve audit", "buffer overflow", "sql injection", "penetration testing"],
        target_tier="frontier",
        target_model="anthropic/claude-opus-5.5",
        target_provider="anthropic",
    ),
    RoutingRule(
        id="quick-greetings-micro",
        name="Micro Greetings & Conversational Pings",
        description="Routes trivial one-word or brief conversational greetings directly to ultra-cheap Mistral Small 4.",
        priority=90,
        pattern=r"(?i)^(hello|hi|hey|bonjour|hola|ciao|good\s+morning|good\s+evening)[.!?\s]*$",
        keywords=["hello", "bonjour", "salut", "hey there"],
        target_tier="cheap",
        target_model="mistral/mistral-small-4",
        target_provider="mistral",
    ),
]


class RoutingRuleManager:
    """
    Manages custom and predefined enterprise routing rules and policy overrides.
    Evaluates prompt messages against pattern and keyword criteria in descending priority.
    """

    def __init__(self, initial_rules: Optional[List[RoutingRule]] = None):
        self._rules: Dict[str, RoutingRule] = {}
        rules_to_load = initial_rules if initial_rules is not None else DEFAULT_RULES
        for r in rules_to_load:
            self._rules[r.id] = r.model_copy()

    def get_all_rules(self) -> List[RoutingRule]:
        return sorted(self._rules.values(), key=lambda r: r.priority, reverse=True)

    def get_rule(self, rule_id: str) -> Optional[RoutingRule]:
        return self._rules.get(rule_id)

    def add_rule(self, rule: RoutingRule) -> RoutingRule:
        self._rules[rule.id] = rule
        return rule

    def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> Optional[RoutingRule]:
        if rule_id not in self._rules:
            return None
        current = self._rules[rule_id].model_dump()
        for k, v in updates.items():
            if k in current and k != "id":
                current[k] = v
        updated = RoutingRule(**current)
        self._rules[rule_id] = updated
        return updated

    def delete_rule(self, rule_id: str) -> bool:
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def reset_defaults(self) -> None:
        self._rules.clear()
        for r in DEFAULT_RULES:
            self._rules[r.id] = r.model_copy()

    def evaluate(self, messages: Any) -> Optional[RuleMatchResult]:
        """
        Evaluate messages against enabled rules in priority order.
        Returns first matched RuleMatchResult, or None.
        """
        if not messages:
            return None

        # Extract full conversation text
        text_parts = []
        for msg in messages:
            if hasattr(msg, "content"):
                text_parts.append(str(msg.content or ""))
            elif isinstance(msg, dict):
                text_parts.append(str(msg.get("content", "")))
        full_text = " ".join(text_parts).strip()
        if not full_text:
            return None

        sorted_rules = self.get_all_rules()

        for rule in sorted_rules:
            if not rule.enabled:
                continue

            matched = False
            matched_reason = ""

            # Check regex pattern
            if rule.pattern:
                try:
                    if re.search(rule.pattern, full_text):
                        matched = True
                        matched_reason = f"Matched pattern: {rule.pattern}"
                except re.error:
                    pass

            # Check keywords if not already matched
            if not matched and rule.keywords:
                full_lower = full_text.lower()
                for kw in rule.keywords:
                    kw_lower = kw.lower()
                    if re.search(rf"\b{re.escape(kw_lower)}\b", full_lower):
                        matched = True
                        matched_reason = f"Matched keyword: '{kw}'"
                        break

            if matched:
                rule.match_count += 1
                return RuleMatchResult(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    target_tier=rule.target_tier,
                    target_model=rule.target_model,
                    target_provider=rule.target_provider,
                    reason=matched_reason,
                )

        return None
