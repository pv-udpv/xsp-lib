"""Type definitions and data classes."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pathlib import Path


class RefactoringActionType(str, Enum):
    """Type of refactoring action."""
    RENAME = "rename"
    MOVE = "move"
    EXTRACT = "extract"
    INLINE = "inline"
    COLLAPSE_CYCLE = "collapse_cycle"
    SPLIT_MODULE = "split_module"


class SeverityLevel(str, Enum):
    """Severity level for observations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RelationType(str, Enum):
    """Types of code relationships."""
    DIRECT_CALL = "direct_call"
    INDIRECT_CALL = "indirect_call"
    INHERITANCE = "inheritance"
    COMPOSITION = "composition"
    IMPORT = "import"
    MUTUAL = "mutual"
    SIBLING = "sibling"
    PARAMETER = "parameter"
    RETURN_VALUE = "return_value"
    EXCEPTION = "exception"


class SourceType(str, Enum):
    """Types of unstructured sources for context linking."""
    LLM_CHAT = "llm_chat"
    MARKDOWN_DOC = "markdown_doc"
    GIT_COMMIT = "git_commit"
    GITHUB_ISSUE = "github_issue"
    DOCSTRING = "docstring"
    CODE_COMMENT = "code_comment"
    ADR = "adr"
    SLACK_MESSAGE = "slack_message"


@dataclass
class Symbol:
    """Represents a code symbol (function, class, variable, etc.)."""
    id: str  # Unique identifier (e.g., "module.py:function_name")
    name: str
    kind: str  # "function", "class", "variable", etc.
    file_path: Path
    line: int
    column: int
    docstring: Optional[str] = None
    parameters: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CodeEdge:
    """Represents a relationship between two symbols."""
    source_id: str
    target_id: str
    relation_type: RelationType
    strength: float = 1.0  # 0-1, how strong the relationship is
    distance: int = 1  # Steps in the call graph
    locations: List[tuple] = field(default_factory=list)  # File locations


@dataclass
class Observation:
    """Represents a code smell or pattern observation."""
    symbol_id: str
    observation_type: str  # "god_module", "dead_code", etc.
    severity: SeverityLevel
    description: str
    suggestion: str
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RefactoringPlan:
    """Plan for a refactoring operation."""
    operation: RefactoringActionType
    target_symbol: str
    files_affected: List[Path] = field(default_factory=list)
    symbols_affected: List[str] = field(default_factory=list)
    risk_score: float = 0.0  # 0-1, higher = riskier
    impact_summary: str = ""
    preview_changes: Dict[str, str] = field(default_factory=dict)  # file -> diff
    estimated_time: float = 0.0  # seconds


@dataclass
class HealthReport:
    """Code health analysis report."""
    health_score: float  # 0-100
    total_symbols: int
    observations: List[Observation] = field(default_factory=list)
    refactoring_opportunities: List[Dict[str, Any]] = field(default_factory=list)
    cycles_found: int = 0
    dead_code_ratio: float = 0.0  # 0-1
    avg_complexity: float = 0.0
    high_coupling_count: int = 0


@dataclass
class SemanticContext:
    """Semantic context linking code to unstructured sources."""
    source_type: SourceType
    relation: str  # "mentions", "documents", "explains", etc.
    snippet: str
    url: str
    confidence: float = 1.0  # 0-1
    embedding: Optional[List[float]] = None
