"""
AXIOM Orchestrator - Coordinates all verification agents for comprehensive analysis.
"""
import asyncio
import hashlib
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

from core.config import Config
from core.token_tracker import TokenTracker
from core.models import VerificationReport, VerificationStatus, VerificationFinding, Severity


class Orchestrator:
    """Coordinates all AXIOM verification agents."""

    def __init__(self):
        self.config = Config()
        self.token_tracker = TokenTracker(self.config.MAX_TOKENS_PER_DAY)
        self._agents = {}
        self._history: List[Dict] = []
        self._load_agents()

    def _load_agents(self):
        """Load all verification agents."""
        from agents.assertion_checker import AssertionChecker
        from agents.logic_analyzer import LogicAnalyzer
        from agents.invariant_detector import InvariantDetector
        from agents.proof_generator import ProofGenerator
        from agents.boundary_analyzer import BoundaryAnalyzer
        from agents.concurrency_verifier import ConcurrencyVerifier
        from agents.specification_validator import SpecificationValidator
        from agents.termination_prover import TerminationProver
        from agents.abstract_interpreter import AbstractInterpreter
        from agents.verification_report import VerificationReporter

        self._agents = {
            "assertion_checker": AssertionChecker(),
            "logic_analyzer": LogicAnalyzer(),
            "invariant_detector": InvariantDetector(),
            "proof_generator": ProofGenerator(),
            "boundary_analyzer": BoundaryAnalyzer(),
            "concurrency_verifier": ConcurrencyVerifier(),
            "specification_validator": SpecificationValidator(),
            "termination_prover": TerminationProver(),
            "abstract_interpreter": AbstractInterpreter(),
            "verification_report": VerificationReporter(),
        }

    async def verify(self, code: str, language: str = "python",
                     agents: Optional[List[str]] = None,
                     context: Optional[Dict] = None) -> VerificationReport:
        """Run full verification pipeline on code."""
        start = time.time()
        context = context or {}
        code_hash = hashlib.sha256(code.encode()).hexdigest()[:16]
        report_id = f"vrf-{code_hash}-{int(time.time())}"

        report = VerificationReport(
            id=report_id,
            code_hash=code_hash,
            language=language,
            timestamp=datetime.now().isoformat(),
        )

        # Select agents to run
        if agents is None:
            agents = list(self._agents.keys())

        # Run agents concurrently
        tasks = []
        for name in agents:
            if name in self._agents:
                agent = self._agents[name]
                ctx = {**context, "language": language, "code_hash": code_hash}
                tasks.append(self._run_agent(name, agent, code, ctx))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect results
        all_findings = []
        for name, result in zip(agents, results):
            if isinstance(result, Exception):
                report.agent_results[name] = {"error": str(result)}
                continue
            report.agent_results[name] = result
            token_est = self.config.AGENT_TOKEN_ESTIMATES.get(name, 15000)
            self.token_tracker.record_usage(name, token_est, "verify")
            report.token_usage[name] = token_est
            # Extract findings
            for f in result.get("findings", []):
                finding = VerificationFinding(
                    id=f.get("id", f"{name}-0"),
                    category=f.get("category", name),
                    severity=Severity(f.get("severity", "medium")),
                    title=f.get("title", ""),
                    description=f.get("description", ""),
                    location=f.get("location", ""),
                    suggestion=f.get("suggestion", ""),
                    confidence=f.get("confidence", 0.8),
                )
                all_findings.append(finding)

        report.findings = all_findings
        report.total_findings = len(all_findings)

        # Compute overall status
        critical = sum(1 for f in all_findings if f.severity == Severity.CRITICAL)
        high = sum(1 for f in all_findings if f.severity == Severity.HIGH)
        if critical > 0:
            report.overall_status = VerificationStatus.DISPROVED
        elif high > 0:
            report.overall_status = VerificationStatus.UNKNOWN
        else:
            report.overall_status = VerificationStatus.PROVED

        # Compute confidence
        if all_findings:
            report.confidence_score = round(
                sum(f.confidence for f in all_findings) / len(all_findings), 3
            )
        else:
            report.confidence_score = 0.95

        report.analysis_duration_ms = round((time.time() - start) * 1000, 2)
        self._history.append({
            "id": report_id,
            "timestamp": report.timestamp,
            "findings": len(all_findings),
            "duration_ms": report.analysis_duration_ms,
        })
        return report

    async def _run_agent(self, name: str, agent, code: str, context: Dict) -> dict:
        """Run a single agent with timeout."""
        try:
            return await asyncio.wait_for(
                agent.analyze(code, context),
                timeout=self.config.AGENT_TIMEOUT
            )
        except asyncio.TimeoutError:
            return {"error": f"Agent {name} timed out", "findings": []}

    def get_status(self) -> dict:
        """Get orchestrator status."""
        return {
            "agents_loaded": len(self._agents),
            "agents": list(self._agents.keys()),
            "token_usage": self.token_tracker.get_usage_summary(),
            "analyses_run": len(self._history),
            "history": self._history[-10:],
        }

    def get_history(self) -> List[Dict]:
        """Get analysis history."""
        return self._history
