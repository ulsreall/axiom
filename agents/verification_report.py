"""
AXIOM Verification Report Agent
Estimated tokens per analysis: ~14,000

Generates comprehensive verification reports combining results from all agents.
Produces proof summaries, counterexamples, confidence scores, and actionable
recommendations for improving code correctness.
"""
import re
import ast
import asyncio
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import Counter


class VerificationReporter:
    """Generates comprehensive verification reports.
    
    Token estimate: ~14,000 per analysis
    - Result aggregation: ~3,000
    - Confidence scoring: ~2,500
    - Counterexample generation: ~3,000
    - Summary generation: ~2,500
    - Recommendation engine: ~2,000
    - Formatting: ~1,000
    """

    def __init__(self):
        self.findings = []

    async def analyze(self, code: str, context: Dict[str, Any] = None) -> dict:
        """Generate a comprehensive verification report."""
        context = context or {}
        self.findings = []
        agent_results = context.get("agent_results", {})
        
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "agent": "verification_report",
                "error": f"Syntax error: {e}",
                "findings": [],
                "summary": "Cannot parse code.",
            }

        # Generate report components
        code_metrics = self._compute_code_metrics(tree, code)
        summary = self._generate_summary(agent_results, code_metrics)
        confidence = self._compute_confidence(agent_results)
        counterexamples = self._generate_counterexamples(agent_results)
        recommendations = self._generate_recommendations(agent_results, tree, code)
        severity_distribution = self._analyze_severity_distribution(agent_results)
        proof_status = self._summarize_proofs(agent_results)

        return {
            "agent": "verification_report",
            "findings": self.findings,
            "report": {
                "summary": summary,
                "confidence_score": confidence,
                "code_metrics": code_metrics,
                "counterexamples": counterexamples,
                "recommendations": recommendations,
                "severity_distribution": severity_distribution,
                "proof_status": proof_status,
                "timestamp": datetime.now().isoformat(),
                "code_hash": hashlib.sha256(code.encode()).hexdigest()[:16],
            },
            "summary": f"Verification report: confidence {confidence:.1%}, {len(recommendations)} recommendations.",
        }

    def _compute_code_metrics(self, tree: ast.AST, code: str) -> dict:
        """Compute code metrics relevant to verification."""
        lines = code.split('\n')
        total_lines = len(lines)
        blank_lines = sum(1 for l in lines if not l.strip())
        comment_lines = sum(1 for l in lines if l.strip().startswith('#'))
        
        functions = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        asserts = [n for n in ast.walk(tree) if isinstance(n, ast.Assert)]
        try_blocks = [n for n in ast.walk(tree) if isinstance(n, ast.Try)]
        imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        
        # Cyclomatic complexity (simplified)
        complexity_nodes = sum(1 for n in ast.walk(tree) 
                              if isinstance(n, (ast.If, ast.For, ast.While, ast.ExceptHandler, 
                                               ast.With, ast.BoolOp)))
        
        return {
            "total_lines": total_lines,
            "code_lines": total_lines - blank_lines - comment_lines,
            "blank_lines": blank_lines,
            "comment_lines": comment_lines,
            "functions": len(functions),
            "classes": len(classes),
            "assertions": len(asserts),
            "try_blocks": len(try_blocks),
            "imports": len(imports),
            "cyclomatic_complexity": complexity_nodes + 1,
            "assertion_density": round(len(asserts) / max(len(functions), 1), 3),
            "comment_ratio": round(comment_lines / max(total_lines, 1), 3),
            "avg_function_length": round(
                sum(len(n.body) for n in functions) / max(len(functions), 1), 1
            ),
        }

    def _generate_summary(self, agent_results: dict, code_metrics: dict) -> dict:
        """Generate high-level verification summary."""
        total_findings = 0
        agent_summaries = {}
        
        for agent_name, result in agent_results.items():
            if isinstance(result, dict) and "findings" in result:
                findings = result["findings"]
                total_findings += len(findings)
                agent_summaries[agent_name] = {
                    "findings_count": len(findings),
                    "summary": result.get("summary", ""),
                    "status": "complete" if "error" not in result else "error",
                }
        
        # Overall assessment
        if total_findings == 0:
            assessment = "PASS"
            description = "No issues found. Code appears correct."
        elif total_findings <= 3:
            assessment = "PASS_WITH_WARNINGS"
            description = f"Minor issues found ({total_findings}). Code is mostly correct."
        elif total_findings <= 10:
            assessment = "NEEDS_REVIEW"
            description = f"Several issues found ({total_findings}). Manual review recommended."
        else:
            assessment = "FAIL"
            description = f"Significant issues found ({total_findings}). Code needs remediation."

        return {
            "assessment": assessment,
            "description": description,
            "total_findings": total_findings,
            "agent_summaries": agent_summaries,
            "code_metrics": code_metrics,
        }

    def _compute_confidence(self, agent_results: dict) -> float:
        """Compute overall verification confidence score."""
        confidences = []
        
        for agent_name, result in agent_results.items():
            if isinstance(result, dict):
                findings = result.get("findings", [])
                proofs = result.get("proofs", [])
                
                # Base confidence from findings
                if not findings:
                    confidences.append(0.95)
                else:
                    critical = sum(1 for f in findings if f.get("severity") == "critical")
                    high = sum(1 for f in findings if f.get("severity") == "high")
                    medium = sum(1 for f in findings if f.get("severity") == "medium")
                    
                    agent_conf = max(0.1, 1.0 - (critical * 0.3 + high * 0.15 + medium * 0.05))
                    confidences.append(agent_conf)
                
                # Boost for proved proofs
                for proof in proofs:
                    if proof.get("status") == "proved":
                        confidences.append(0.95)
                    elif proof.get("status") == "disproved":
                        confidences.append(0.1)

        if not confidences:
            return 0.5
        
        # Weighted average
        return round(sum(confidences) / len(confidences), 3)

    def _generate_counterexamples(self, agent_results: dict) -> List[dict]:
        """Generate counterexamples from failed proofs."""
        counterexamples = []
        
        for agent_name, result in agent_results.items():
            if not isinstance(result, dict):
                continue
            
            findings = result.get("findings", [])
            for finding in findings:
                if finding.get("severity") in ("critical", "high"):
                    counterexample = {
                        "finding_id": finding.get("id", "unknown"),
                        "agent": agent_name,
                        "description": finding.get("description", ""),
                        "location": finding.get("location", ""),
                        "trigger_conditions": finding.get("trigger_conditions", ""),
                        "suggested_fix": finding.get("suggestion", ""),
                    }
                    counterexamples.append(counterexample)
        
        return counterexamples[:10]  # Limit to top 10

    def _generate_recommendations(self, agent_results: dict, tree: ast.AST, code: str) -> List[dict]:
        """Generate actionable recommendations."""
        recommendations = []
        priority = 1
        
        # Collect all suggestions
        for agent_name, result in agent_results.items():
            if not isinstance(result, dict):
                continue
            for finding in result.get("findings", []):
                if finding.get("suggestion"):
                    recommendations.append({
                        "priority": priority,
                        "agent": agent_name,
                        "finding": finding.get("title", ""),
                        "suggestion": finding["suggestion"],
                        "severity": finding.get("severity", "low"),
                    })
                    priority += 1
        
        # Add general recommendations based on code analysis
        functions = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        has_docstrings = sum(
            1 for f in functions
            if f.body and isinstance(f.body[0], ast.Expr) and isinstance(f.body[0].value, ast.Constant)
        )
        
        if len(functions) > 0 and has_docstrings / len(functions) < 0.5:
            recommendations.append({
                "priority": priority,
                "agent": "verification_report",
                "finding": "Low documentation coverage",
                "suggestion": "Add docstrings to at least 50% of functions for better verifiability.",
                "severity": "low",
            })
            priority += 1

        asserts = sum(1 for _ in ast.walk(tree) if isinstance(_, ast.Assert))
        if asserts < len(functions) and len(functions) > 2:
            recommendations.append({
                "priority": priority,
                "agent": "verification_report",
                "finding": "Low assertion density",
                "suggestion": "Add assertions to verify pre/post conditions in key functions.",
                "severity": "medium",
            })

        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        recommendations.sort(key=lambda r: severity_order.get(r.get("severity", "info"), 4))
        
        return recommendations[:15]

    def _analyze_severity_distribution(self, agent_results: dict) -> dict:
        """Analyze distribution of finding severities."""
        counts = Counter()
        
        for agent_name, result in agent_results.items():
            if isinstance(result, dict):
                for finding in result.get("findings", []):
                    severity = finding.get("severity", "info")
                    counts[severity] += 1
        
        return {
            "critical": counts.get("critical", 0),
            "high": counts.get("high", 0),
            "medium": counts.get("medium", 0),
            "low": counts.get("low", 0),
            "info": counts.get("info", 0),
            "total": sum(counts.values()),
        }

    def _summarize_proofs(self, agent_results: dict) -> dict:
        """Summarize proof statuses across all agents."""
        proved = 0
        disproved = 0
        unknown = 0
        
        for agent_name, result in agent_results.items():
            if isinstance(result, dict):
                for proof in result.get("proofs", []):
                    status = proof.get("status", "unknown")
                    if status == "proved":
                        proved += 1
                    elif status == "disproved":
                        disproved += 1
                    else:
                        unknown += 1
                
                for proof in result.get("proof_obligations", []):
                    status = proof.get("status", "unknown")
                    if status == "proved":
                        proved += 1
                    elif status == "disproved":
                        disproved += 1
                    else:
                        unknown += 1
        
        total = proved + disproved + unknown
        return {
            "total_proofs": total,
            "proved": proved,
            "disproved": disproved,
            "unknown": unknown,
            "proof_rate": round(proved / max(total, 1), 3),
        }
