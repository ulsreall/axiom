"""
AXIOM Boundary Analyzer Agent
Estimated tokens per analysis: ~16,000

Analyzes boundary conditions including integer overflow, array bounds,
edge cases, and off-by-one errors. Checks for safe arithmetic operations
and proper boundary handling.
"""
import re
import ast
import asyncio
from typing import Dict, List, Any, Optional, Set


class BoundaryAnalyzer:
    """Analyzes boundary conditions and edge cases in code.
    
    Token estimate: ~16,000 per analysis
    - AST parsing: ~2,500
    - Integer overflow analysis: ~3,500
    - Array bounds checking: ~3,000
    - Edge case detection: ~3,000
    - Off-by-one analysis: ~2,000
    - Report generation: ~2,000
    """

    def __init__(self):
        self.findings = []
        self.boundary_conditions = []

    async def analyze(self, code: str, context: Dict[str, Any] = None) -> dict:
        """Analyze boundary conditions and edge cases."""
        context = context or {}
        self.findings = []
        self.boundary_conditions = []

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "agent": "boundary_analyzer",
                "error": f"Syntax error: {e}",
                "findings": [],
                "summary": "Cannot parse code.",
            }

        # Run all boundary analyses
        self._check_integer_overflow(tree, code)
        self._check_array_bounds(tree, code)
        self._check_division_by_zero(tree)
        self._check_off_by_one(tree, code)
        self._check_empty_collections(tree)
        self._check_none_access(tree)
        self._check_string_boundaries(tree)
        self._check_floating_point_edge_cases(tree)
        self._check_large_number_handling(tree)

        return {
            "agent": "boundary_analyzer",
            "findings": self.findings,
            "boundary_conditions": self.boundary_conditions,
            "summary": f"Found {len(self.boundary_conditions)} boundary conditions and {len(self.findings)} issues.",
            "metrics": {
                "total_boundaries": len(self.boundary_conditions),
                "overflow_risks": sum(1 for b in self.boundary_conditions if b["kind"] == "overflow"),
                "bounds_risks": sum(1 for b in self.boundary_conditions if b["kind"] == "array_bounds"),
                "division_risks": sum(1 for b in self.boundary_conditions if b["kind"] == "division_by_zero"),
                "off_by_one_risks": sum(1 for b in self.boundary_conditions if b["kind"] == "off_by_one"),
                "findings_by_severity": {
                    "critical": sum(1 for f in self.findings if f.get("severity") == "critical"),
                    "high": sum(1 for f in self.findings if f.get("severity") == "high"),
                    "medium": sum(1 for f in self.findings if f.get("severity") == "medium"),
                    "low": sum(1 for f in self.findings if f.get("severity") == "low"),
                }
            }
        }

    def _check_integer_overflow(self, tree: ast.AST, code: str):
        """Check for potential integer overflow risks."""
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
                # Check for multiplication that could overflow
                if isinstance(node.left, ast.Constant) and isinstance(node.right, ast.Constant):
                    result = node.left.value * node.right.value
                    if result > 2**63:
                        self.findings.append({
                            "id": f"BOUND-OVERFLOW-{node.lineno}",
                            "category": "boundary_analyzer",
                            "severity": "high",
                            "title": "Integer overflow in multiplication",
                            "description": f"Line {node.lineno}: {node.left.value} * {node.right.value} = {result}, exceeds 64-bit range.",
                            "location": f"line {node.lineno}",
                            "confidence": 0.95,
                        })
                
                self.boundary_conditions.append({
                    "kind": "overflow",
                    "description": "Multiplication operation - check for overflow",
                    "location": f"line {node.lineno}",
                    "risk_level": "medium",
                    "trigger_conditions": "Large operands",
                    "mitigation": "Use arbitrary precision or check before multiply",
                })

            elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
                # Exponentiation can easily overflow
                if isinstance(node.right, ast.Constant) and isinstance(node.right.value, int):
                    if node.right.value > 100:
                        self.findings.append({
                            "id": f"BOUND-POWER-{node.lineno}",
                            "category": "boundary_analyzer",
                            "severity": "medium",
                            "title": "Large exponentiation",
                            "description": f"Line {node.lineno}: Exponent {node.right.value} may produce extremely large number.",
                            "location": f"line {node.lineno}",
                            "confidence": 0.8,
                        })

            elif isinstance(node, ast.AugAssign):
                if isinstance(node.op, ast.Add) or isinstance(node.op, ast.Mult):
                    self.boundary_conditions.append({
                        "kind": "overflow",
                        "description": f"Augmented {type(node.op).__name__} assignment - potential overflow",
                        "location": f"line {node.lineno}",
                        "risk_level": "low",
                        "mitigation": "Check bounds before operation",
                    })

    def _check_array_bounds(self, tree: ast.AST, code: str):
        """Check for potential array/list index out of bounds."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript):
                # Check for constant negative index
                if isinstance(node.slice, ast.Constant):
                    idx = node.slice.value
                    if isinstance(idx, int) and idx < 0:
                        self.boundary_conditions.append({
                            "kind": "array_bounds",
                            "description": f"Negative index ({idx}) - relies on non-empty collection",
                            "location": f"line {node.lineno}",
                            "risk_level": "medium",
                            "trigger_conditions": "Empty collection",
                            "mitigation": "Check length before indexing",
                        })
                    elif isinstance(idx, int) and idx > 100:
                        self.findings.append({
                            "id": f"BOUND-HIGH-INDEX-{node.lineno}",
                            "category": "boundary_analyzer",
                            "severity": "low",
                            "title": "High constant index",
                            "description": f"Line {node.lineno}: Accessing index {idx} may be out of bounds.",
                            "location": f"line {node.lineno}",
                            "confidence": 0.5,
                        })

                # Check for slice operations
                if isinstance(node.slice, ast.Slice):
                    # Check for [:100] or similar large slices
                    for bound in [node.slice.lower, node.slice.upper]:
                        if isinstance(bound, ast.Constant) and isinstance(bound.value, int):
                            if bound.value > 10000:
                                self.findings.append({
                                    "id": f"BOUND-LARGE-SLICE-{node.lineno}",
                                    "category": "boundary_analyzer",
                                    "severity": "low",
                                    "title": "Large slice bound",
                                    "description": f"Line {node.lineno}: Slice bound {bound.value} may be excessive.",
                                    "location": f"line {node.lineno}",
                                    "confidence": 0.5,
                                })

                # Check for dictionary access without .get()
                if isinstance(node.value, ast.Name) and isinstance(node.slice, (ast.Constant, ast.Name)):
                    self.boundary_conditions.append({
                        "kind": "key_error",
                        "description": f"Direct dict access - may raise KeyError",
                        "location": f"line {node.lineno}",
                        "risk_level": "medium",
                        "mitigation": "Use .get() with default or check key existence",
                    })

    def _check_division_by_zero(self, tree: ast.AST):
        """Check for potential division by zero."""
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp):
                is_division = isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod))
                
                if is_division:
                    # Check if divisor is constant zero
                    if isinstance(node.right, ast.Constant) and node.right.value == 0:
                        self.findings.append({
                            "id": f"BOUND-DIV-ZERO-{node.lineno}",
                            "category": "boundary_analyzer",
                            "severity": "critical",
                            "title": "Division by zero",
                            "description": f"Line {node.lineno}: Division by constant zero.",
                            "location": f"line {node.lineno}",
                            "confidence": 0.99,
                        })
                    elif isinstance(node.right, ast.Constant):
                        # Non-zero constant - safe
                        pass
                    else:
                        self.boundary_conditions.append({
                            "kind": "division_by_zero",
                            "description": f"Division by non-constant expression",
                            "location": f"line {node.lineno}",
                            "risk_level": "high",
                            "trigger_conditions": "Divisor evaluates to zero",
                            "mitigation": "Add divisor != 0 check before division",
                        })

    def _check_off_by_one(self, tree: ast.AST, code: str):
        """Check for potential off-by-one errors."""
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                if isinstance(node.iter, ast.Call) and hasattr(node.iter.func, 'id'):
                    if node.iter.func.id == 'range':
                        args = node.iter.args
                        # Check range(len(x)) pattern
                        if (len(args) == 1 and isinstance(args[0], ast.Call) and
                            hasattr(args[0].func, 'id') and args[0].func.id == 'len'):
                            self.boundary_conditions.append({
                                "kind": "off_by_one",
                                "description": "range(len(x)) - verify boundary access is correct",
                                "location": f"line {node.lineno}",
                                "risk_level": "low",
                                "mitigation": "Verify index usage matches iteration bounds",
                            })
                        
                        # Check for range(n+1) or range(n-1) patterns
                        if args and isinstance(args[-1], ast.BinOp):
                            if isinstance(args[-1].op, (ast.Add, ast.Sub)):
                                self.boundary_conditions.append({
                                    "kind": "off_by_one",
                                    "description": f"range() with arithmetic bound - check for off-by-one",
                                    "location": f"line {node.lineno}",
                                    "risk_level": "medium",
                                    "mitigation": "Verify the bound calculation is correct",
                                })

            # Check for < vs <= comparisons near boundaries
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                op = node.ops[0]
                if isinstance(op, (ast.Lt, ast.LtE)):
                    if isinstance(node.comparators[0], ast.Call):
                        if hasattr(node.comparators[0].func, 'id') and node.comparators[0].func.id == 'len':
                            if isinstance(op, ast.Lt):
                                self.boundary_conditions.append({
                                    "kind": "off_by_one",
                                    "description": "x < len(arr) - standard safe bound check",
                                    "location": f"line {node.lineno}",
                                    "risk_level": "info",
                                })

    def _check_empty_collections(self, tree: ast.AST):
        """Check for operations on potentially empty collections."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript):
                # Direct indexing without length check
                if isinstance(node.value, ast.Name):
                    self.boundary_conditions.append({
                        "kind": "empty_collection",
                        "description": f"Direct indexing of '{self._expr_to_str(node.value)}' - may be empty",
                        "location": f"line {node.lineno}",
                        "risk_level": "medium",
                        "trigger_conditions": "Empty collection",
                        "mitigation": "Check len() > 0 before indexing",
                    })

            # Check for min/max on potentially empty iterables
            if isinstance(node, ast.Call) and hasattr(node.func, 'id'):
                if node.func.id in ('min', 'max', 'sum', 'sorted'):
                    self.boundary_conditions.append({
                        "kind": "empty_collection",
                        "description": f"{node.func.id}() on potentially empty iterable",
                        "location": f"line {node.lineno}",
                        "risk_level": "medium",
                        "trigger_conditions": f"Empty argument to {node.func.id}()",
                        "mitigation": "Check for non-empty collection or provide default",
                    })

    def _check_none_access(self, tree: ast.AST):
        """Check for attribute access on potentially None values."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                # Check if the name could be None
                if node.value.id in ('result', 'data', 'value', 'response', 'item', 'output'):
                    self.boundary_conditions.append({
                        "kind": "none_access",
                        "description": f"Attribute access on '{node.value.id}' - may be None",
                        "location": f"line {node.lineno}",
                        "risk_level": "medium",
                        "trigger_conditions": "Variable is None",
                        "mitigation": "Add None check before attribute access",
                    })

    def _check_string_boundaries(self, tree: ast.AST):
        """Check string operation boundary conditions."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and hasattr(node.func, 'attr'):
                method = node.func.attr
                if method in ('split', 'strip', 'replace', 'find', 'index'):
                    self.boundary_conditions.append({
                        "kind": "string_bounds",
                        "description": f"String.{method}() - check for empty string handling",
                        "location": f"line {node.lineno}",
                        "risk_level": "low",
                        "trigger_conditions": "Empty string input",
                    })

            # Check for string indexing
            if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Constant):
                if isinstance(node.value.value, str):
                    if isinstance(node.slice, ast.Constant):
                        idx = node.slice.value
                        if isinstance(idx, int) and abs(idx) >= len(node.value.value):
                            self.findings.append({
                                "id": f"BOUND-STR-INDEX-{node.lineno}",
                                "category": "boundary_analyzer",
                                "severity": "high",
                                "title": "String index out of bounds",
                                "description": f"Line {node.lineno}: Index {idx} out of bounds for string of length {len(node.value.value)}.",
                                "location": f"line {node.lineno}",
                                "confidence": 0.95,
                            })

    def _check_floating_point_edge_cases(self, tree: ast.AST):
        """Check for floating point edge cases."""
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
                # Check for potential floating point precision issues
                if isinstance(node.right, ast.Constant):
                    val = node.right.value
                    if isinstance(val, float):
                        # Check for very small denominators
                        if 0 < abs(val) < 1e-10:
                            self.findings.append({
                                "id": f"BOUND-FP-PRECISION-{node.lineno}",
                                "category": "boundary_analyzer",
                                "severity": "medium",
                                "title": "Floating point precision risk",
                                "description": f"Line {node.lineno}: Division by very small float ({val}) may cause precision issues.",
                                "location": f"line {node.lineno}",
                                "confidence": 0.75,
                            })

            # Check for NaN/infinity comparisons
            if isinstance(node, ast.Compare):
                for comp in node.comparators:
                    if isinstance(comp, ast.Constant) and isinstance(comp.value, float):
                        if comp.value == float('inf') or comp.value != comp.value:  # NaN
                            self.findings.append({
                                "id": f"BOUND-FP-EDGE-{node.lineno}",
                                "category": "boundary_analyzer",
                                "severity": "low",
                                "title": "Floating point edge comparison",
                                "description": f"Line {node.lineno}: Comparison with float edge case ({comp.value}).",
                                "location": f"line {node.lineno}",
                                "confidence": 0.7,
                            })

    def _check_large_number_handling(self, tree: ast.AST):
        """Check for handling of very large numbers."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, int):
                if abs(node.value) > 2**31:
                    self.boundary_conditions.append({
                        "kind": "large_number",
                        "description": f"Large constant: {node.value}",
                        "location": f"line {node.lineno}",
                        "risk_level": "low",
                        "mitigation": "Verify this value is intentional and fits expected ranges",
                    })

    def _expr_to_str(self, node: ast.AST) -> str:
        """Convert expression to string."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Attribute):
            return f"{self._expr_to_str(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call) and hasattr(node.func, 'id'):
            return f"{node.func.id}(...)"
        return f"<{type(node).__name__}>"
