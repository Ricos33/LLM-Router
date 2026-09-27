from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ModelTier(str, Enum):
    CHEAP = "cheap"
    FRONTIER = "frontier"


class ClassificationResult(BaseModel):
    tier: ModelTier
    confidence: float = Field(ge=0.0, le=1.0)
    score: float = Field(ge=0.0, le=1.0, description="Complexity score (0.0 to 1.0)")
    reasons: List[str] = Field(default_factory=list)
    suggested_model: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
