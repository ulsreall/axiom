"""
AXIOM Data Models - Core data structures for verification results.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum


class VerificationStatus(Enum):
    PROVED = "proved"
    DISPROVED = "disproved"
    UNKNOWN = "unknown"
    TIMEOUT = "timeout"
    ERROR = "error"


class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class ProofObligation:
    """A single proof obligation arising from verification."""
    id: str
    description: str
    location: str  # file:line
    status: VerificationStatus = VerificationStatus.UNKNOWN
    evidence: str = ""
    confidence: float = 0.0


@dataclass
class Assertion:
    """Represents a code assertion (pre/post condition, invariant)."""
    kind: str  # "precondition", "postcondition", "invariant", "assert"
    expression: str
    location: str
    holds: Optional[bool] = None
    counterexample: Optional[str] = None


@dataclass
class VerificationFinding:
    """A finding from the verification process."""
    id: str
    category: str
    severity: Severity
    title: str
    description: str
    location: str = ""
    suggestion: str = ""
    confidence: float = 0.0


@dataclass
class Invariant:
    """A discovered or verified invariant."""
    expression: str
    kind: str  # "loop", "class", "data", "global"
    location: str
    is_maintained: Optional[bool] = None
    proof_sketch: str = ""


@dataclass
class TerminationArgument:
    """A termination proof argument."""
    function_name: str
    ranking_function: str
    well_founded_relation: str
    is_decreasing: Optional[bool] = None
    proof: str = ""


@dataclass
class ConcurrencyIssue:
    """A concurrency-related finding."""
    kind: str  # "race_condition", "deadlock", "atomicity_violation"
    description: str
    involved_resources: List[str] = field(default_factory=list)
    execution_trace: str = ""
    severity: Severity = Severity.MEDIUM


@dataclass
class AbstractDomain:
    """Result from abstract interpretation."""
    domain_type: str  # "interval", "sign", "equality", "octagon", "polyhedra"
    variables: Dict[str, Any] = field(default_factory=dict)
    is_safe: bool = True
    over_approximation_bound: str = ""


@dataclass
class VerificationReport:
    """Complete verification report combining all analyses."""
    id: str
    code_hash: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    language: str = "python"
    overall_status: VerificationStatus = VerificationStatus.UNKNOWN
    confidence_score: float = 0.0
    total_findings: int = 0
    findings: List[VerificationFinding] = field(default_factory=list)
    proof_obligations: List[ProofObligation] = field(default_factory=list)
    assertions: List[Assertion] = field(default_factory=list)
    invariants: List[Invariant] = field(default_factory=list)
    termination_arguments: List[TerminationArgument] = field(default_factory=list)
    concurrency_issues: List[ConcurrencyIssue] = field(default_factory=list)
    abstract_domains: List[AbstractDomain] = field(default_factory=list)
    agent_results: Dict[str, Any] = field(default_factory=dict)
    token_usage: Dict[str, int] = field(default_factory=dict)
    analysis_duration_ms: float = 0.0


@dataclass
class LogicFormula:
    """Represents a propositional or first-order logic formula."""
    expression: str
    formula_type: str  # "propositional", "first_order", "temporal"
    is_satisfiable: Optional[bool] = None
    is_valid: Optional[bool] = None
    model: Optional[Dict[str, Any]] = None
    countermodel: Optional[Dict[str, Any]] = None


@dataclass
class BoundaryCondition:
    """Represents a boundary condition or edge case."""
    kind: str  # "overflow", "underflow", "array_bounds", "division_by_zero", "edge_case"
    description: str
    location: str
    risk_level: Severity = Severity.MEDIUM
    trigger_conditions: str = ""
    mitigation: str = ""


@dataclass
class ContractViolation:
    """A violation of a function/method contract."""
    function_name: str
    contract_type: str  # "precondition", "postcondition", "invariant"
    violated_condition: str
    inputs_that_cause_violation: str = ""
    location: str = ""
