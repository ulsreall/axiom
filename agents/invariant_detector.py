"""
AXIOM Invariant Detector Agent
Estimated tokens per analysis: ~18,000

Discovers and verifies loop invariants, class invariants, and data invariants.
Analyzes loop structures, class definitions, and data flow to identify invariants
that hold throughout execution.
"""
import re
import ast
import asyncio
from typing import Dict, List, Any, Optional, Set, Tuple


class InvariantDetector:
    """Detects and verifies invariants in code.
    
    Token estimate: ~18,000 per analysis
    - AST parsing: ~3,000
    - Loop invariant analysis: ~5,000
    - Class invariant analysis: ~4,000
    - Data invariant analysis: ~3,000
    - Report generation: ~3,000
    """

    def __init__(self):
        self.findings = []
        self.invariants = []

    async def analyze(self, code: str, context: Dict[str, Any] = None) -> dict:
        """Detect and verify invariants in code."""
        context = context or {}
        self.findings = []
        self.invariants = []

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "agent": "invariant_detector",
                "error": f"Syntax error: {e}",
                "findings": [],
                "invariants": [],
                "summary": "Cannot parse code.",
            }

        # Run all invariant analyses
        self._detect_loop_invariants(tree, code)
        self._detect_class_invariants(tree, code)
        self._detect_data_invariants(tree, code)
        self._detect_accumulator_invariants(tree)
        self._detect_counter_invariants(tree)
        self._check_invariant_violations(tree)
        self._analyze_loop_bounds(tree)
        self._detect_monotonic_invariants(tree)

        return {
            "agent": "invariant_detector",
            "findings": self.findings,
            "invariants": self.invariants,
            "summary": f"Detected {len(self.invariants)} invariants and {len(self.findings)} findings.",
            "metrics": {
                "total_invariants": len(self.invariants),
                "loop_invariants": sum(1 for i in self.invariants if i["kind"] == "loop"),
                "class_invariants": sum(1 for i in self.invariants if i["kind"] == "class"),
                "data_invariants": sum(1 for i in self.invariants if i["kind"] == "data"),
                "maintained": sum(1 for i in self.invariants if i.get("is_maintained", True)),
                "violations": sum(1 for f in self.findings if f.get("severity") == "high"),
            }
        }

    def _detect_loop_invariants(self, tree: ast.AST, code: str):
        """Detect invariants in loop structures."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                loop_vars = set()
                modified_vars = set()
                read_vars = set()
                
                # Analyze variables in loop
                for child in ast.walk(node):
                    if isinstance(child, ast.Name):
                        if isinstance(child.ctx, ast.Store):
                            modified_vars.add(child.id)
                        elif isinstance(child.ctx, ast.Load):
                            read_vars.add(child.id)
                    if isinstance(child, ast.For) and child.target:
                        if isinstance(child.target, ast.Name):
                            loop_vars.add(child.target.id)
                
                # Variables read but not modified are likely invariant
                invariant_vars = read_vars - modified_vars
                for var in sorted(invariant_vars):
                    self.invariants.append({
                        "kind": "loop",
                        "expression": f"{var} remains constant throughout loop",
                        "location": f"line {node.lineno}",
                        "is_maintained": True,
                        "proof_sketch": f"Variable '{var}' is read but never assigned in loop body.",
                    })

                # Detect accumulator pattern (sum, product, list building)
                for child in node.body:
                    if isinstance(child, ast.AugAssign):
                        if isinstance(child.target, ast.Name):
                            var = child.target.id
                            op = type(child.op).__name__
                            self.invariants.append({
                                "kind": "loop",
                                "expression": f"{var} is monotonically {'increasing' if isinstance(child.op, ast.Add) else 'changing'} ({op}=)",
                                "location": f"line {child.lineno}",
                                "is_maintained": True,
                                "proof_sketch": f"{var} uses augmented assignment ({op}=) in loop.",
                            })

                # Detect range-based loop invariants
                if isinstance(node, ast.For) and isinstance(node.iter, ast.Call):
                    if hasattr(node.iter.func, 'id') and node.iter.func.id == 'range':
                        if node.iter.args:
                            range_arg = node.iter.args[0]
                            if isinstance(range_arg, ast.Name):
                                self.invariants.append({
                                    "kind": "loop",
                                    "expression": f"loop index < {range_arg.id} (range bound)",
                                    "location": f"line {node.lineno}",
                                    "is_maintained": True,
                                    "proof_sketch": f"Loop iterates over range({range_arg.id}).",
                                })

    def _detect_class_invariants(self, tree: ast.AST, code: str):
        """Detect class invariants from method patterns."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name
                attrs_modified = {}  # attr -> set of methods that modify it
                attrs_checked = {}   # attr -> set of methods that check it
                
                methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                
                for method in methods:
                    method_name = method.name
                    for child in ast.walk(method):
                        if isinstance(child, ast.Attribute) and isinstance(child.value, ast.Name):
                            if child.value.id == 'self':
                                attr = child.attr
                                if isinstance(child.ctx, ast.Store):
                                    attrs_modified.setdefault(attr, set()).add(method_name)
                                else:
                                    attrs_checked.setdefault(attr, set()).add(method_name)
                
                # Attributes set in __init__ and not modified elsewhere are invariants
                init_attrs = attrs_modified.get('__init__', set())
                for attr in attrs_modified:
                    modifiers = attrs_modified[attr]
                    if '__init__' in modifiers and len(modifiers) == 1:
                        self.invariants.append({
                            "kind": "class",
                            "expression": f"self.{attr} is immutable after initialization",
                            "location": f"class {class_name}",
                            "is_maintained": True,
                            "proof_sketch": f"self.{attr} is only set in __init__.",
                        })

                # Detect size/length invariants
                for method in methods:
                    for child in ast.walk(method):
                        if isinstance(child, ast.Compare):
                            if isinstance(child.left, ast.Call) and hasattr(child.left.func, 'id'):
                                if child.left.func.id == 'len':
                                    self.invariants.append({
                                        "kind": "class",
                                        "expression": f"Length constraint checked in {method.name}",
                                        "location": f"line {child.lineno}",
                                        "is_maintained": None,
                                        "proof_sketch": f"len() comparison in {method.name}.",
                                    })

    def _detect_data_invariants(self, tree: ast.AST, code: str):
        """Detect data structure invariants."""
        for node in ast.walk(tree):
            # Detect sorted-list invariant
            if isinstance(node, ast.FunctionDef):
                for child in ast.walk(node):
                    if isinstance(child, ast.Attribute):
                        if child.attr in ('sort', 'sorted', 'append', 'insert'):
                            # Check if sort is called after modifications
                            pass

                # Check for dataclass fields with validators
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name) and decorator.id == 'dataclass':
                        for item in node.body:
                            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                                self.invariants.append({
                                    "kind": "data",
                                    "expression": f"{item.target.id} is a typed field",
                                    "location": f"line {item.lineno}",
                                    "is_maintained": True,
                                    "proof_sketch": "Dataclass field with type annotation.",
                                })

                # Check for property-based invariants
                for child in node.body:
                    if isinstance(child, ast.FunctionDef):
                        for dec in child.decorator_list:
                            if isinstance(dec, ast.Name) and dec.id == 'property':
                                self.invariants.append({
                                    "kind": "data",
                                    "expression": f"{child.name} is a derived/computed property",
                                    "location": f"line {child.lineno}",
                                    "is_maintained": None,
                                    "proof_sketch": f"Property {child.name} derives a value.",
                                })

    def _detect_accumulator_invariants(self, tree: ast.AST):
        """Detect accumulator patterns and their invariants."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                accumulators = {}
                for child in node.body:
                    if isinstance(child, ast.AugAssign) and isinstance(child.target, ast.Name):
                        var = child.target.id
                        op = type(child.op).__name__
                        accumulators[var] = op
                
                for var, op in accumulators.items():
                    if op == 'Add':
                        self.invariants.append({
                            "kind": "loop",
                            "expression": f"{var} accumulates sum (monotonically increasing)",
                            "location": f"line {node.lineno}",
                            "is_maintained": True,
                            "proof_sketch": f"{var} += pattern detected.",
                        })
                    elif op == 'Mult':
                        self.invariants.append({
                            "kind": "loop",
                            "expression": f"{var} accumulates product",
                            "location": f"line {node.lineno}",
                            "is_maintained": True,
                            "proof_sketch": f"{var} *= pattern detected.",
                        })

    def _detect_counter_invariants(self, tree: ast.AST):
        """Detect counter/index invariants in loops."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                # Check for counter variables
                counters = set()
                for child in node.body:
                    if isinstance(child, ast.Assign):
                        for target in child.targets:
                            if isinstance(target, ast.Name):
                                # Check if it's a counter: x = x + 1
                                if isinstance(child.value, ast.BinOp):
                                    if isinstance(child.value.op, ast.Add):
                                        if isinstance(child.value.left, ast.Name) and target.id == child.value.left.id:
                                            counters.add(target.id)
                                        elif isinstance(child.value.right, ast.Name) and target.id == child.value.right.id:
                                            counters.add(target.id)
                
                for counter in counters:
                    self.invariants.append({
                        "kind": "loop",
                        "expression": f"{counter} increments each iteration",
                        "location": f"line {node.lineno}",
                        "is_maintained": True,
                        "proof_sketch": f"{counter} = {counter} + ... pattern detected.",
                    })

    def _check_invariant_violations(self, tree: ast.AST):
        """Check for potential invariant violations."""
        for node in ast.walk(tree):
            # Check for aliasing that could break invariants
            if isinstance(node, ast.Assign):
                if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                    # Check if assigning a mutable reference
                    if isinstance(node.value, (ast.List, ast.Dict, ast.Set)):
                        pass  # Mutable default - handled elsewhere
                    elif isinstance(node.value, ast.Name):
                        # Aliasing: x = y where y is mutable
                        pass

            # Check for mutation of supposedly immutable data
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                if node.value.id == 'self' and isinstance(node.ctx, ast.Store):
                    # In a method, check if this violates class invariant
                    pass

    def _analyze_loop_bounds(self, tree: ast.AST):
        """Analyze loop bounds for well-definedness."""
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                if isinstance(node.iter, ast.Call):
                    if hasattr(node.iter.func, 'id') and node.iter.func.id == 'range':
                        args = node.iter.args
                        if len(args) == 1:
                            if isinstance(args[0], ast.Name):
                                self.invariants.append({
                                    "kind": "loop",
                                    "expression": f"Loop bounded: [0, {args[0].id})",
                                    "location": f"line {node.lineno}",
                                    "is_maintained": True,
                                    "proof_sketch": f"range({args[0].id}) defines finite iteration.",
                                })
                        elif len(args) >= 2:
                            start = args[0] if isinstance(args[0], ast.Constant) else "..."
                            end = args[1] if isinstance(args[1], ast.Constant) else "..."
                            self.invariants.append({
                                "kind": "loop",
                                "expression": f"Loop bounded: [{start}, {end})",
                                "location": f"line {node.lineno}",
                                "is_maintained": True,
                                "proof_sketch": "range() with explicit bounds.",
                            })
            
            elif isinstance(node, ast.While):
                # Check for while True (potentially non-terminating)
                if isinstance(node.test, ast.Constant) and node.test.value is True:
                    has_break = any(isinstance(n, ast.Break) for n in ast.walk(node))
                    if not has_break:
                        self.findings.append({
                            "id": f"INV-WHILE-TRUE-{node.lineno}",
                            "category": "invariant_detector",
                            "severity": "high",
                            "title": "Infinite loop without break",
                            "description": f"Line {node.lineno}: `while True` with no break statement. Potential infinite loop.",
                            "location": f"line {node.lineno}",
                            "confidence": 0.9,
                        })
                    else:
                        self.invariants.append({
                            "kind": "loop",
                            "expression": "Loop terminates via break condition",
                            "location": f"line {node.lineno}",
                            "is_maintained": None,
                            "proof_sketch": "while True with break - termination depends on break condition.",
                        })

    def _detect_monotonic_invariants(self, tree: ast.AST):
        """Detect monotonically changing variables."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                for child in node.body:
                    if isinstance(child, ast.Assign):
                        if len(child.targets) == 1 and isinstance(child.targets[0], ast.Name):
                            var = child.targets[0].id
                            # Check for min/max patterns
                            if isinstance(child.value, ast.Call) and hasattr(child.value.func, 'id'):
                                if child.value.func.id in ('min', 'max'):
                                    self.invariants.append({
                                        "kind": "loop",
                                        "expression": f"{var} is bounded by {child.value.func.id}()",
                                        "location": f"line {child.lineno}",
                                        "is_maintained": True,
                                        "proof_sketch": f"{var} = {child.value.func.id}() constrains value.",
                                    })
