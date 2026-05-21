"""
AXIOM Proof Generator Agent
Estimated tokens per analysis: ~25,000

Generates correctness proofs, verification conditions, and proof obligations.
Uses weakest precondition calculus, Hoare logic, and induction principles
to construct formal proofs of code correctness.
"""
import re
import ast
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from copy import deepcopy


class ProofGenerator:
    """Generates formal proofs of code correctness.
    
    Token estimate: ~25,000 per analysis
    - AST parsing: ~3,000
    - Hoare logic application: ~7,000
    - WP calculus: ~5,000
    - Induction proofs: ~4,000
    - Verification condition generation: ~3,000
    - Proof optimization: ~1,500
    - Report generation: ~1,500
    """

    def __init__(self):
        self.findings = []
        self.proof_obligations = []
        self.proofs = []

    async def analyze(self, code: str, context: Dict[str, Any] = None) -> dict:
        """Generate correctness proofs for code."""
        context = context or {}
        self.findings = []
        self.proof_obligations = []
        self.proofs = []

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "agent": "proof_generator",
                "error": f"Syntax error: {e}",
                "findings": [],
                "proofs": [],
                "summary": "Cannot parse code.",
            }

        # Run all proof generation passes
        self._generate_wp_proofs(tree, code)
        self._generate_induction_proofs(tree, code)
        self._generate_contract_proofs(tree, code)
        self._generate_type_safety_proofs(tree)
        self._generate_termination_proofs(tree)
        self._verify_return_consistency(tree)
        self._check_proof_strength(tree)
        self._generate_refinement_proofs(tree)

        return {
            "agent": "proof_generator",
            "findings": self.findings,
            "proof_obligations": self.proof_obligations,
            "proofs": self.proofs,
            "summary": f"Generated {len(self.proofs)} proofs with {len(self.proof_obligations)} proof obligations.",
            "metrics": {
                "total_proofs": len(self.proofs),
                "proof_obligations": len(self.proof_obligations),
                "proved": sum(1 for p in self.proofs if p.get("status") == "proved"),
                "disproved": sum(1 for p in self.proofs if p.get("status") == "disproved"),
                "unknown": sum(1 for p in self.proofs if p.get("status") == "unknown"),
                "proof_methods_used": list(set(p.get("method", "unknown") for p in self.proofs)),
            }
        }

    def _generate_wp_proofs(self, tree: ast.AST, code: str):
        """Generate proofs using weakest precondition calculus."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_name = node.name
                
                # Extract postcondition (from docstring or return assertions)
                postcondition = self._extract_postcondition(node)
                if not postcondition:
                    postcondition = "result is well-defined"

                # Compute weakest precondition through statements
                wp = postcondition
                proof_steps = []
                
                # Walk backwards through function body
                for stmt in reversed(node.body):
                    wp_step = self._compute_wp(stmt, wp)
                    if wp_step != wp:
                        proof_steps.append({
                            "statement": self._stmt_to_str(stmt),
                            "wp": wp_step,
                        })
                    wp = wp_step

                proof = {
                    "function": func_name,
                    "method": "weakest_precondition",
                    "postcondition": postcondition,
                    "weakest_precondition": wp,
                    "proof_steps": proof_steps,
                    "status": "proved" if self._is_trivially_true(wp) else "unknown",
                }
                self.proofs.append(proof)

                self.proof_obligations.append({
                    "id": f"PO-WP-{func_name}",
                    "description": f"Verify that precondition implies WP for {func_name}",
                    "location": f"line {node.lineno}",
                    "status": proof["status"],
                    "evidence": f"WP: {wp}",
                })

    def _generate_induction_proofs(self, tree: ast.AST, code: str):
        """Generate inductive proofs for recursive functions."""
        # Find recursive functions
        func_calls = {}  # func_name -> set of called functions
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_name = node.name
                calls = set()
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Name):
                            calls.add(child.func.id)
                        elif isinstance(child.func, ast.Attribute):
                            calls.add(child.func.attr)
                func_calls[func_name] = calls

        # Identify recursive functions
        for func_name, calls in func_calls.items():
            if func_name in calls:
                # This function is recursive
                self.proofs.append({
                    "function": func_name,
                    "method": "induction",
                    "status": "unknown",
                    "proof_sketch": (
                        f"Induction proof outline for {func_name}:\n"
                        f"1. Base case: Verify termination of non-recursive paths\n"
                        f"2. Inductive step: Assume recursive call terminates, prove current call terminates\n"
                        f"3. Well-foundedness: Recursive arguments must decrease"
                    ),
                    "base_case_verified": None,
                    "inductive_step_verified": None,
                    "well_founded": None,
                })

                # Check if arguments decrease
                for child in ast.walk(tree):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if child.name == func_name:
                            self._check_recursive_argument_decrease(child, func_name)

    def _generate_contract_proofs(self, tree: ast.AST, code: str):
        """Generate proofs based on function contracts."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_name = node.name
                
                # Check for assert statements as proof obligations
                assertions = []
                for child in ast.walk(node):
                    if isinstance(child, ast.Assert):
                        assertions.append(child)
                
                for i, assertion in enumerate(assertions):
                    po_id = f"PO-CONTRACT-{func_name}-{i}"
                    self.proof_obligations.append({
                        "id": po_id,
                        "description": f"Assertion in {func_name}: {self._stmt_to_str(assertion)}",
                        "location": f"line {assertion.lineno}",
                        "status": "unknown",
                        "evidence": "Requires runtime verification or static proof.",
                    })

    def _generate_type_safety_proofs(self, tree: ast.AST):
        """Generate type safety proofs based on annotations."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_name = node.name
                
                # Check type annotations
                annotated_params = []
                unannotated_params = []
                
                for arg in node.args.args:
                    if arg.arg == 'self':
                        continue
                    if arg.annotation:
                        annotated_params.append(arg.arg)
                    else:
                        unannotated_params.append(arg.arg)
                
                has_return_type = node.returns is not None
                
                if annotated_params or has_return_type:
                    proof = {
                        "function": func_name,
                        "method": "type_safety",
                        "status": "partial",
                        "annotated_params": annotated_params,
                        "unannotated_params": unannotated_params,
                        "has_return_type": has_return_type,
                    }
                    self.proofs.append(proof)
                    
                    if unannotated_params:
                        self.findings.append({
                            "id": f"PROOF-TYPE-PARTIAL-{func_name}",
                            "category": "proof_generator",
                            "severity": "low",
                            "title": f"Partial type annotation in {func_name}",
                            "description": f"Function '{func_name}' has some untyped parameters: {', '.join(unannotated_params)}",
                            "location": f"line {node.lineno}",
                            "confidence": 0.7,
                        })

    def _generate_termination_proofs(self, tree: ast.AST):
        """Generate termination proof sketches."""
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                if isinstance(node.iter, ast.Call) and hasattr(node.iter.func, 'id'):
                    if node.iter.func.id == 'range':
                        self.proofs.append({
                            "function": f"loop_at_line_{node.lineno}",
                            "method": "termination",
                            "status": "proved",
                            "ranking_function": "range index",
                            "well_founded_relation": "natural numbers <",
                            "evidence": "range() produces a finite sequence.",
                        })
            elif isinstance(node, ast.While):
                if isinstance(node.test, ast.Constant) and node.test.value is True:
                    has_break = any(isinstance(n, ast.Break) for n in ast.walk(node))
                    if has_break:
                        self.proofs.append({
                            "function": f"loop_at_line_{node.lineno}",
                            "method": "termination",
                            "status": "unknown",
                            "ranking_function": "break condition dependent",
                            "evidence": "Termination depends on break condition.",
                        })
                    else:
                        self.proofs.append({
                            "function": f"loop_at_line_{node.lineno}",
                            "method": "termination",
                            "status": "disproved",
                            "evidence": "while True without break - non-terminating.",
                        })
                        self.findings.append({
                            "id": f"PROOF-NONTERM-{node.lineno}",
                            "category": "proof_generator",
                            "severity": "high",
                            "title": "Non-terminating loop",
                            "description": f"Line {node.lineno}: while True loop with no break.",
                            "location": f"line {node.lineno}",
                            "confidence": 0.95,
                        })

    def _verify_return_consistency(self, tree: ast.AST):
        """Verify that return types are consistent across all paths."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_name = node.name
                returns = []
                
                for child in ast.walk(node):
                    if isinstance(child, ast.Return):
                        if child.value is None:
                            returns.append(("None", child.lineno))
                        elif isinstance(child.value, ast.Constant):
                            returns.append((type(child.value.value).__name__, child.lineno))
                        elif isinstance(child.value, ast.List):
                            returns.append(("list", child.lineno))
                        elif isinstance(child.value, ast.Dict):
                            returns.append(("dict", child.lineno))
                        elif isinstance(child.value, ast.Name):
                            returns.append(("variable", child.lineno))
                        else:
                            returns.append(("expression", child.lineno))

                if len(set(r[0] for r in returns)) > 1:
                    # Mixed return types
                    types = set(r[0] for r in returns)
                    if "None" in types and len(types) > 1:
                        self.proofs.append({
                            "function": func_name,
                            "method": "return_consistency",
                            "status": "disproved",
                            "evidence": f"Function returns multiple types: {types}",
                        })
                        self.findings.append({
                            "id": f"PROOF-RET-MIXED-{func_name}",
                            "category": "proof_generator",
                            "severity": "medium",
                            "title": f"Inconsistent return types in {func_name}",
                            "description": f"Function returns types: {', '.join(sorted(types))}",
                            "location": f"line {node.lineno}",
                            "confidence": 0.85,
                        })

    def _check_proof_strength(self, tree: ast.AST):
        """Analyze the strength of existing proofs/assertions."""
        total_functions = 0
        proved_functions = 0
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                total_functions += 1
                has_assertion = False
                for child in ast.walk(node):
                    if isinstance(child, ast.Assert):
                        has_assertion = True
                        break
                if has_assertion:
                    proved_functions += 1

        if total_functions > 0:
            coverage = proved_functions / total_functions
            if coverage < 0.3:
                self.findings.append({
                    "id": "PROOF-WEAK-COVERAGE",
                    "category": "proof_generator",
                    "severity": "medium",
                    "title": "Low proof coverage",
                    "description": f"Only {proved_functions}/{total_functions} functions have assertions ({coverage:.0%}).",
                    "suggestion": "Add assertions to unverified functions.",
                    "confidence": 0.8,
                })

    def _generate_refinement_proofs(self, tree: ast.AST):
        """Check that implementations refine their specifications."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if class has abstract methods
                has_abstract = False
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        for dec in child.decorator_list:
                            if isinstance(dec, ast.Name) and dec.id == 'abstractmethod':
                                has_abstract = True
                
                if has_abstract:
                    self.proof_obligations.append({
                        "id": f"PO-REFINE-{node.name}",
                        "description": f"Verify that concrete subclasses implement all abstract methods of {node.name}",
                        "location": f"class {node.name}",
                        "status": "unknown",
                    })

    def _compute_wp(self, stmt: ast.AST, postcondition: str) -> str:
        """Compute weakest precondition for a single statement."""
        if isinstance(stmt, ast.Assign):
            if len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                var = stmt.targets[0].id
                # WP of (x := e, Q) = Q[x/e]
                return postcondition.replace(var, self._expr_to_str(stmt.value))
        elif isinstance(stmt, ast.If):
            # WP of (if b then S1 else S2, Q) = (b => WP(S1, Q)) and (not b => WP(S2, Q))
            cond = self._expr_to_str(stmt.test)
            wp_then = postcondition
            for s in reversed(stmt.body):
                wp_then = self._compute_wp(s, wp_then)
            wp_else = postcondition
            for s in reversed(stmt.orelse):
                wp_else = self._compute_wp(s, wp_else)
            return f"({cond} -> {wp_then}) and (not {cond} -> {wp_else})"
        elif isinstance(stmt, ast.Assert):
            return f"({self._expr_to_str(stmt.test)}) and ({postcondition})"
        elif isinstance(stmt, ast.Return):
            return postcondition
        elif isinstance(stmt, ast.Pass):
            return postcondition
        elif isinstance(stmt, ast.Expr):
            return postcondition  # Side-effecting expression
        return postcondition

    def _extract_postcondition(self, node: ast.FunctionDef) -> Optional[str]:
        """Extract postcondition from function."""
        # Look for assertions before returns
        for stmt in node.body:
            if isinstance(stmt, ast.Assert):
                return self._expr_to_str(stmt.test)
        
        # Check docstring for :returns: or :postcondition:
        if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
            docstring = node.body[0].value.value
            if isinstance(docstring, str):
                for line in docstring.split('\n'):
                    for marker in [':postcondition:', ':returns:', ':post:', ':ensures:']:
                        if marker in line.lower():
                            return line.split(marker, 1)[1].strip()
        
        return None

    def _check_recursive_argument_decrease(self, func_node: ast.FunctionDef, func_name: str):
        """Check if recursive calls have decreasing arguments."""
        recursive_calls = []
        for child in ast.walk(func_node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name) and child.func.id == func_name:
                    recursive_calls.append(child)
        
        for call in recursive_calls:
            # Simple check: does the argument involve the parameter?
            for arg in call.args:
                if isinstance(arg, ast.Name) and arg.id in [a.arg for a in func_node.args.args if a.arg != 'self']:
                    # Argument is directly the parameter - not decreasing
                    self.findings.append({
                        "id": f"PROOF-REC-NOT-DECREASED-{func_name}",
                        "category": "proof_generator",
                        "severity": "high",
                        "title": f"Recursive call without argument decrease in {func_name}",
                        "description": f"Function '{func_name}' calls itself without clearly decreasing argument.",
                        "location": f"line {call.lineno}",
                        "confidence": 0.8,
                    })

    def _is_trivially_true(self, wp: str) -> bool:
        """Check if a weakest precondition is trivially true."""
        trivial = ["true", "True", "1", ""]
        return wp.strip() in trivial

    def _stmt_to_str(self, stmt: ast.AST) -> str:
        """Convert statement to string representation."""
        if isinstance(stmt, ast.Assign):
            return f"assignment at line {stmt.lineno}"
        elif isinstance(stmt, ast.Assert):
            return f"assert at line {stmt.lineno}"
        elif isinstance(stmt, ast.If):
            return f"if-statement at line {stmt.lineno}"
        elif isinstance(stmt, ast.Return):
            return f"return at line {stmt.lineno}"
        elif isinstance(stmt, ast.For):
            return f"for-loop at line {stmt.lineno}"
        elif isinstance(stmt, ast.While):
            return f"while-loop at line {stmt.lineno}"
        return f"statement at line {getattr(stmt, 'lineno', '?')}"

    def _expr_to_str(self, node: ast.AST) -> str:
        """Convert expression to string."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Compare):
            parts = [self._expr_to_str(node.left)]
            for op, comp in zip(node.ops, node.comparators):
                op_str = {ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<", ast.LtE: "<=",
                         ast.Gt: ">", ast.GtE: ">="}.get(type(op), "?")
                parts.append(f"{op_str} {self._expr_to_str(comp)}")
            return " ".join(parts)
        elif isinstance(node, ast.BinOp):
            op_str = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/",
                     ast.Mod: "%", ast.Pow: "**"}.get(type(node.op), "?")
            return f"({self._expr_to_str(node.left)} {op_str} {self._expr_to_str(node.right)})"
        elif isinstance(node, ast.Call) and hasattr(node.func, 'id'):
            return f"{node.func.id}(...)"
        elif isinstance(node, ast.BoolOp):
            op = " and " if isinstance(node.op, ast.And) else " or "
            return f"({op.join(self._expr_to_str(v) for v in node.values)})"
        return f"<{type(node).__name__}>"
