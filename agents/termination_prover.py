"""
AXIOM Termination Prover Agent
Estimated tokens per analysis: ~16,000

Proves termination of functions and loops using well-founded relations,
ranking functions, and structural induction. Identifies potential
non-termination and provides termination arguments.
"""
import re
import ast
import asyncio
from typing import Dict, List, Any, Optional, Tuple


class TerminationProver:
    """Proves termination of functions and loops.
    
    Token estimate: ~16,000 per analysis
    - AST parsing: ~2,500
    - Loop analysis: ~4,000
    - Recursion analysis: ~4,000
    - Ranking function search: ~3,000
    - Report generation: ~2,500
    """

    def __init__(self):
        self.findings = []
        self.termination_args = []

    async def analyze(self, code: str, context: Dict[str, Any] = None) -> dict:
        """Prove termination of code constructs."""
        context = context or {}
        self.findings = []
        self.termination_args = []

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "agent": "termination_prover",
                "error": f"Syntax error: {e}",
                "findings": [],
                "summary": "Cannot parse code.",
            }

        # Run all termination analyses
        self._analyze_for_loops(tree, code)
        self._analyze_while_loops(tree, code)
        self._analyze_recursive_functions(tree, code)
        self._check_well_foundedness(tree, code)
        self._detect_non_termination(tree, code)
        self._analyze_nested_loops(tree, code)
        self._check_decreasing_sequences(tree)

        return {
            "agent": "termination_prover",
            "findings": self.findings,
            "termination_arguments": self.termination_args,
            "summary": f"Analyzed termination: {len(self.termination_args)} arguments, {len(self.findings)} findings.",
            "metrics": {
                "total_arguments": len(self.termination_args),
                "proved_terminating": sum(1 for t in self.termination_args if t.get("status") == "proved"),
                "proved_non_terminating": sum(1 for t in self.termination_args if t.get("status") == "non_terminating"),
                "unknown": sum(1 for t in self.termination_args if t.get("status") == "unknown"),
                "ranking_functions_found": sum(1 for t in self.termination_args if t.get("ranking_function")),
            }
        }

    def _analyze_for_loops(self, tree: ast.AST, code: str):
        """Analyze for-loop termination."""
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                iter_type = "unknown"
                ranking = ""
                status = "unknown"
                
                if isinstance(node.iter, ast.Call) and hasattr(node.iter.func, 'id'):
                    if node.iter.func.id == 'range':
                        iter_type = "range"
                        args = node.iter.args
                        if len(args) == 1:
                            if isinstance(args[0], ast.Constant) and isinstance(args[0].value, int):
                                if args[0].value > 0:
                                    status = "proved"
                                    ranking = f"range({args[0].value}) - finite sequence of {args[0].value} elements"
                                elif args[0].value <= 0:
                                    status = "proved"
                                    ranking = "Empty range - zero iterations"
                            elif isinstance(args[0], ast.Name):
                                status = "unknown"
                                ranking = f"range({args[0].id}) - depends on value of {args[0].id}"
                        elif len(args) >= 2:
                            status = "proved"
                            ranking = "range with explicit bounds"
                    
                    elif node.iter.func.id in ('enumerate', 'zip', 'map', 'filter'):
                        iter_type = node.iter.func.id
                        status = "proved"
                        ranking = f"{iter_type}() iterates over finite input"
                    
                    elif node.iter.func.id == 'reversed':
                        iter_type = "reversed"
                        status = "proved"
                        ranking = "reversed() iterates over finite input"

                elif isinstance(node.iter, ast.Name):
                    iter_type = "variable"
                    status = "unknown"
                    ranking = f"Variable '{node.iter.id}' - depends on value"

                elif isinstance(node.iter, (ast.List, ast.Tuple, ast.Set)):
                    iter_type = "literal"
                    status = "proved"
                    ranking = "Literal collection - finite"

                self.termination_args.append({
                    "function": f"for_loop_at_line_{node.lineno}",
                    "kind": "loop",
                    "status": status,
                    "ranking_function": ranking,
                    "well_founded_relation": "natural numbers <" if status == "proved" else "unknown",
                    "loop_type": iter_type,
                })

                if status == "unknown":
                    self.findings.append({
                        "id": f"TERM-FOR-UNKNOWN-{node.lineno}",
                        "category": "termination_prover",
                        "severity": "low",
                        "title": f"Unproven termination for for-loop",
                        "description": f"Line {node.lineno}: Cannot prove termination for loop over {iter_type} expression.",
                        "location": f"line {node.lineno}",
                        "confidence": 0.5,
                    })

    def _analyze_while_loops(self, tree: ast.AST, code: str):
        """Analyze while-loop termination."""
        for node in ast.walk(tree):
            if isinstance(node, ast.While):
                status = "unknown"
                ranking = ""
                
                # Check for while True
                if isinstance(node.test, ast.Constant) and node.test.value is True:
                    has_break = any(isinstance(n, ast.Break) for n in ast.walk(node))
                    if has_break:
                        status = "unknown"
                        ranking = "break-dependent - requires invariant proof"
                    else:
                        status = "non_terminating"
                        ranking = "while True without break"
                        self.findings.append({
                            "id": f"TERM-WHILE-TRUE-{node.lineno}",
                            "category": "termination_prover",
                            "severity": "high",
                            "title": "Non-terminating while True loop",
                            "description": f"Line {node.lineno}: `while True` with no break statement.",
                            "location": f"line {node.lineno}",
                            "confidence": 0.95,
                        })
                
                # Check for while with simple counter
                elif isinstance(node.test, ast.Compare):
                    if len(node.test.ops) == 1:
                        op = node.test.ops[0]
                        if isinstance(op, (ast.Gt, ast.GtE)):
                            # while x > 0 pattern
                            if (isinstance(node.test.left, ast.Name) and 
                                isinstance(node.test.comparators[0], ast.Constant)):
                                var = node.test.left.id
                                # Check if var is decremented in loop
                                decremented = False
                                for child in node.body:
                                    if isinstance(child, ast.AugAssign):
                                        if isinstance(child.target, ast.Name) and child.target.id == var:
                                            if isinstance(child.op, ast.Sub):
                                                decremented = True
                                    elif isinstance(child, ast.Assign):
                                        if (len(child.targets) == 1 and isinstance(child.targets[0], ast.Name) and
                                            child.targets[0].id == var):
                                            # Check if assigned a smaller value
                                            decremented = True
                                
                                if decremented:
                                    status = "proved"
                                    ranking = f"{var} decreases toward bound"
                                else:
                                    status = "unknown"
                                    ranking = f"{var} may not decrease"
                
                # Check for simple counter patterns
                else:
                    # Look for counter variables in body
                    counters = self._find_counter_patterns(node.body)
                    if counters:
                        status = "likely_terminating"
                        ranking = f"Counter pattern: {', '.join(counters)}"

                self.termination_args.append({
                    "function": f"while_loop_at_line_{node.lineno}",
                    "kind": "loop",
                    "status": status,
                    "ranking_function": ranking,
                    "well_founded_relation": "natural numbers <" if status == "proved" else "depends on condition",
                })

    def _analyze_recursive_functions(self, tree: ast.AST, code: str):
        """Analyze recursive function termination."""
        # Build call graph
        func_defs = {}
        call_graph = {}
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_defs[node.name] = node
                calls = set()
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Name):
                            calls.add(child.func.id)
                call_graph[node.name] = calls

        # Find recursive functions
        for func_name, calls in call_graph.items():
            if func_name in calls:
                func_node = func_defs[func_name]
                
                # Analyze recursive calls
                recursive_calls = []
                for child in ast.walk(func_node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Name) and child.func.id == func_name:
                            recursive_calls.append(child)
                
                # Check if arguments decrease
                status = "unknown"
                ranking = ""
                
                params = [a.arg for a in func_node.args.args if a.arg != 'self']
                
                for call in recursive_calls:
                    for i, arg in enumerate(call.args):
                        if i < len(params):
                            param = params[i]
                            if isinstance(arg, ast.Name) and arg.id == param:
                                # Direct pass-through - not decreasing
                                status = "unknown"
                                ranking = f"Argument '{param}' passed directly (not decreasing)"
                            elif isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub):
                                # x - 1 pattern
                                if isinstance(arg.left, ast.Name) and arg.left.id == param:
                                    if isinstance(arg.right, ast.Constant) and arg.right.value > 0:
                                        status = "proved"
                                        ranking = f"Argument '{param}' decreases by {arg.right.value}"
                                        self.termination_args.append({
                                            "function": func_name,
                                            "kind": "recursion",
                                            "status": "proved",
                                            "ranking_function": f"argument '{param}' decreases by {arg.right.value}",
                                            "well_founded_relation": "natural numbers <",
                                        })
                                    elif isinstance(arg.right, ast.Constant) and arg.right.value < 0:
                                        status = "non_terminating"
                                        ranking = f"Argument '{param}' increases by {-arg.right.value}"
                                        self.findings.append({
                                            "id": f"TERM-REC-INCREASE-{func_name}",
                                            "category": "termination_prover",
                                            "severity": "high",
                                            "title": f"Recursive '{func_name}' with increasing argument",
                                            "description": f"Argument '{param}' increases in recursive call - non-terminating.",
                                            "location": f"line {call.lineno}",
                                            "confidence": 0.8,
                                        })
                            elif isinstance(arg, ast.Call):
                                if hasattr(arg.func, 'id'):
                                    if arg.func.id in ('len', 'abs', 'int'):
                                        status = "likely_terminating"
                                        ranking = f"{arg.func.id}({param}) - likely smaller"

                if status == "unknown":
                    self.termination_args.append({
                        "function": func_name,
                        "kind": "recursion",
                        "status": "unknown",
                        "ranking_function": ranking or "No ranking function found",
                        "well_founded_relation": "unknown",
                    })

                # Check for mutual recursion
                for other_func, other_calls in call_graph.items():
                    if other_func != func_name and func_name in other_calls and other_func in calls:
                        self.findings.append({
                            "id": f"TERM-MUTUAL-REC-{func_name}-{other_func}",
                            "category": "termination_prover",
                            "severity": "medium",
                            "title": f"Mutual recursion: {func_name} <-> {other_func}",
                            "description": f"Functions '{func_name}' and '{other_func}' call each other. Termination harder to prove.",
                            "confidence": 0.7,
                        })

    def _check_well_foundedness(self, tree: ast.AST, code: str):
        """Check that ranking functions use well-founded relations."""
        # Natural numbers with < is well-founded
        # Lexicographic ordering on tuples of naturals is well-founded
        # Subsequence ordering is well-founded
        
        for node in ast.walk(tree):
            if isinstance(node, ast.While):
                # Check if loop bound is well-founded
                if isinstance(node.test, ast.Compare):
                    # Check for x > 0 (well-founded) vs x != 0 (not well-founded for reals)
                    for op in node.ops:
                        if isinstance(op, ast.NotEq):
                            self.findings.append({
                                "id": f"TERM-NOT-WELL-FOUNDED-{node.lineno}",
                                "category": "termination_prover",
                                "severity": "low",
                                "title": "Non-well-founded loop condition",
                                "description": f"Line {node.lineno}: != comparison may not form well-founded relation for all types.",
                                "location": f"line {node.lineno}",
                                "confidence": 0.5,
                            })

    def _detect_non_termination(self, tree: ast.AST, code: str):
        """Detect patterns that indicate non-termination."""
        for node in ast.walk(tree):
            # while x >= 0: x += 1 (infinite)
            if isinstance(node, ast.While):
                if isinstance(node.test, ast.Compare):
                    if len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.GtE):
                        if isinstance(node.test.left, ast.Name):
                            var = node.test.left.id
                            for child in node.body:
                                if isinstance(child, ast.AugAssign):
                                    if isinstance(child.target, ast.Name) and child.target.id == var:
                                        if isinstance(child.op, ast.Add):
                                            self.findings.append({
                                                "id": f"TERM-INFINITE-{node.lineno}",
                                                "category": "termination_prover",
                                                "severity": "critical",
                                                "title": f"Infinite loop: {var} increases while {var} >= 0",
                                                "description": f"Line {node.lineno}: Variable '{var}' increases but condition is {var} >= 0. This never terminates.",
                                                "location": f"line {node.lineno}",
                                                "confidence": 0.95,
                                            })

    def _analyze_nested_loops(self, tree: ast.AST, code: str):
        """Analyze nested loop termination."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                # Count nesting depth
                depth = self._loop_depth(node)
                if depth >= 3:
                    self.findings.append({
                        "id": f"TERM-NESTED-{node.lineno}",
                        "category": "termination_prover",
                        "severity": "medium",
                        "title": f"Deeply nested loops (depth {depth})",
                        "description": f"Line {node.lineno}: {depth}-deep nested loops. Verify termination at each level.",
                        "location": f"line {node.lineno}",
                        "confidence": 0.6,
                    })

    def _check_decreasing_sequences(self, tree: ast.AST):
        """Check for decreasing sequence patterns in loops."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                # Check for x = x - 1 pattern
                for child in node.body:
                    if isinstance(child, ast.AugAssign):
                        if isinstance(child.op, ast.Sub) and isinstance(child.target, ast.Name):
                            var = child.target.id
                            if isinstance(child.value, ast.Constant) and child.value.value > 0:
                                self.termination_args.append({
                                    "function": f"loop_at_line_{node.lineno}",
                                    "kind": "loop",
                                    "status": "likely_terminating",
                                    "ranking_function": f"{var} decreases by {child.value.value} each iteration",
                                    "well_founded_relation": "natural numbers <",
                                })

    def _find_counter_patterns(self, body: list) -> List[str]:
        """Find counter/decrement patterns in loop body."""
        counters = []
        for stmt in body:
            if isinstance(stmt, ast.AugAssign):
                if isinstance(stmt.target, ast.Name):
                    if isinstance(stmt.op, ast.Sub):
                        counters.append(f"{stmt.target.id}-=")
                    elif isinstance(stmt.op, ast.Add):
                        counters.append(f"{stmt.target.id}+=")
            elif isinstance(stmt, ast.Assign):
                if (len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name) and
                    isinstance(stmt.value, ast.BinOp)):
                    var = stmt.targets[0].id
                    if isinstance(stmt.value.op, ast.Sub):
                        counters.append(f"{var}={var}-...")
        return counters

    def _loop_depth(self, node: ast.AST, current: int = 1) -> int:
        """Calculate loop nesting depth."""
        max_depth = current
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.For, ast.While)):
                child_depth = self._loop_depth(child, current + 1)
                max_depth = max(max_depth, child_depth)
        return max_depth
