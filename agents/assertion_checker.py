"""
AXIOM Assertion Checker Agent
Estimated tokens per analysis: ~20,000

Checks preconditions, postconditions, invariants, and contracts in code.
Analyzes assert statements, docstring contracts, decorator-based contracts,
and type annotations for correctness and completeness.
"""
import re
import ast
import asyncio
from typing import Dict, List, Any, Optional


class AssertionChecker:
    """Verifies assertions, contracts, pre/post conditions in code.
    
    Token estimate: ~20,000 per analysis
    - Parsing & AST analysis: ~4,000
    - Contract extraction: ~5,000
    - Assertion validation: ~6,000
    - Report generation: ~3,000
    - Overhead: ~2,000
    """

    def __init__(self):
        self.findings = []
        self.assertions = []

    async def analyze(self, code: str, context: Dict[str, Any] = None) -> dict:
        """Analyze code for assertion correctness and contract completeness."""
        context = context or {}
        self.findings = []
        self.assertions = []
        
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "agent": "assertion_checker",
                "error": f"Syntax error: {e}",
                "findings": [],
                "assertions": [],
                "summary": "Cannot parse code due to syntax error.",
            }

        # Run all checks
        self._check_assert_statements(tree, code)
        self._check_preconditions(tree, code)
        self._check_postconditions(tree, code)
        self._check_contract_decorators(tree, code)
        self._check_type_contracts(tree, code)
        self._check_none_guard_assertions(tree, code)
        self._check_loop_assertions(tree, code)
        self._check_return_assertions(tree, code)

        # Analyze assertion density
        total_functions = sum(1 for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)))
        assert_count = len(self.assertions)
        density = assert_count / max(total_functions, 1)
        
        if density < 0.5 and total_functions > 2:
            self.findings.append({
                "id": "ASSERT-LOW-DENSITY",
                "category": "assertion_checker",
                "severity": "medium",
                "title": "Low assertion density",
                "description": f"Only {assert_count} assertions across {total_functions} functions (density: {density:.2f}). Consider adding more assertions for verification.",
                "suggestion": "Add pre/post conditions and loop invariants to improve verification coverage.",
                "confidence": 0.75,
            })

        return {
            "agent": "assertion_checker",
            "assertions": [a for a in self.assertions],
            "findings": self.findings,
            "summary": f"Found {len(self.assertions)} assertions and {len(self.findings)} findings.",
            "metrics": {
                "total_assertions": len(self.assertions),
                "total_functions": total_functions,
                "assertion_density": round(density, 3),
                "precondition_count": sum(1 for a in self.assertions if a["kind"] == "precondition"),
                "postcondition_count": sum(1 for a in self.assertions if a["kind"] == "postcondition"),
                "invariant_count": sum(1 for a in self.assertions if a["kind"] == "invariant"),
            }
        }

    def _check_assert_statements(self, tree: ast.AST, code: str):
        """Check assert statements for common issues."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Assert):
                # Extract assertion expression
                try:
                    expr = ast.dump(node.test)
                except:
                    expr = "<complex>"
                
                self.assertions.append({
                    "kind": "assert",
                    "expression": self._ast_to_source(node.test, code),
                    "location": f"line {node.lineno}",
                })

                # Check for trivial assertions
                if isinstance(node.test, ast.Constant):
                    if node.test.value is True:
                        self.findings.append({
                            "id": f"ASSERT-TRIVIAL-{node.lineno}",
                            "category": "assertion_checker",
                            "severity": "low",
                            "title": "Trivial assertion",
                            "description": f"Line {node.lineno}: `assert True` is a no-op and provides no verification value.",
                            "location": f"line {node.lineno}",
                            "confidence": 0.95,
                        })
                    elif node.test.value is False:
                        self.findings.append({
                            "id": f"ASSERT-FAIL-{node.lineno}",
                            "category": "assertion_checker",
                            "severity": "high",
                            "title": "Always-failing assertion",
                            "description": f"Line {node.lineno}: `assert False` will always raise AssertionError.",
                            "location": f"line {node.lineno}",
                            "confidence": 0.99,
                        })

                # Check assert with message
                if node.msg is None:
                    self.findings.append({
                        "id": f"ASSERT-NO-MSG-{node.lineno}",
                        "category": "assertion_checker",
                        "severity": "info",
                        "title": "Assertion without message",
                        "description": f"Line {node.lineno}: Assertion has no failure message. Add a message for debugging.",
                        "location": f"line {node.lineno}",
                        "confidence": 0.8,
                    })

    def _check_preconditions(self, tree: ast.AST, code: str):
        """Extract and verify preconditions from function bodies."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_name = node.name
                preconditions = []
                
                # Look for early assertions that check parameters
                for stmt in node.body:
                    if isinstance(stmt, ast.Assert):
                        preconditions.append(stmt)
                    elif isinstance(stmt, ast.If):
                        # Check for if-raise patterns (alternative to assert)
                        if (isinstance(stmt.test, ast.UnaryOp) and 
                            isinstance(stmt.test.op, ast.Not)):
                            preconditions.append(stmt)
                        # Check for isinstance guards
                        elif isinstance(stmt.test, ast.Call):
                            if hasattr(stmt.test.func, 'id') and stmt.test.func.id == 'isinstance':
                                preconditions.append(stmt)

                for pre in preconditions:
                    self.assertions.append({
                        "kind": "precondition",
                        "expression": self._ast_to_source(pre, code) if hasattr(pre, 'test') else "<guard>",
                        "location": f"{func_name}:line {pre.lineno}",
                    })

                # Check if functions with parameters have any preconditions
                if node.args.args and not preconditions:
                    # Check for type annotations as implicit contracts
                    annotated = sum(1 for arg in node.args.args if arg.annotation is not None)
                    if annotated == 0 and func_name not in ('__init__', '__str__', '__repr__'):
                        self.findings.append({
                            "id": f"PRECOND-MISSING-{func_name}",
                            "category": "assertion_checker",
                            "severity": "low",
                            "title": f"No preconditions for {func_name}",
                            "description": f"Function '{func_name}' has {len(node.args.args)} parameters but no precondition checks or type annotations.",
                            "location": f"line {node.lineno}",
                            "suggestion": "Add type annotations or input validation assertions.",
                            "confidence": 0.6,
                        })

    def _check_postconditions(self, tree: ast.AST, code: str):
        """Check for postcondition assertions before return statements."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_name = node.name
                postconditions = []
                
                # Look for assertions before return statements
                for i, stmt in enumerate(node.body):
                    if isinstance(stmt, ast.Return) and i > 0:
                        prev = node.body[i - 1]
                        if isinstance(prev, ast.Assert):
                            postconditions.append(prev)
                
                for post in postconditions:
                    self.assertions.append({
                        "kind": "postcondition",
                        "expression": self._ast_to_source(post, code),
                        "location": f"{func_name}:line {post.lineno}",
                    })

    def _check_contract_decorators(self, tree: ast.AST, code: str):
        """Check for contract-based decorators (@require, @ensure, @invariant)."""
        contract_decorators = {
            'require': 'precondition',
            'ensure': 'postcondition',
            'invariant': 'invariant',
            'precondition': 'precondition',
            'postcondition': 'postcondition',
            'contract': 'contract',
            'validate': 'validation',
        }
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    deco_name = None
                    if isinstance(decorator, ast.Name):
                        deco_name = decorator.id
                    elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
                        deco_name = decorator.func.id
                    elif isinstance(decorator, ast.Attribute):
                        deco_name = decorator.attr
                    
                    if deco_name and deco_name.lower() in contract_decorators:
                        self.assertions.append({
                            "kind": contract_decorators[deco_name.lower()],
                            "expression": f"@{deco_name}",
                            "location": f"{node.name}:line {node.lineno}",
                        })

    def _check_type_contracts(self, tree: ast.AST, code: str):
        """Check type annotations as implicit contracts."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_name = node.name
                
                # Check return type annotation
                if node.returns is None and func_name not in ('__init__',):
                    # Check if there's a docstring describing return type
                    has_docstring = (node.body and isinstance(node.body[0], ast.Expr) and 
                                    isinstance(node.body[0].value, ast.Constant))
                    if not has_docstring:
                        self.findings.append({
                            "id": f"TYPE-NO-RET-{func_name}",
                            "category": "assertion_checker",
                            "severity": "info",
                            "title": f"No return type for {func_name}",
                            "description": f"Function '{func_name}' lacks return type annotation and docstring.",
                            "location": f"line {node.lineno}",
                            "confidence": 0.7,
                        })

                # Check parameter annotations
                for arg in node.args.args:
                    if arg.arg == 'self':
                        continue
                    if arg.annotation is None:
                        self.findings.append({
                            "id": f"TYPE-NO-ANNOT-{func_name}-{arg.arg}",
                            "category": "assertion_checker",
                            "severity": "info",
                            "title": f"Untyped parameter: {arg.arg}",
                            "description": f"Parameter '{arg.arg}' in '{func_name}' has no type annotation.",
                            "location": f"line {node.lineno}",
                            "confidence": 0.65,
                        })

    def _check_none_guard_assertions(self, tree: ast.AST, code: str):
        """Check for None-safety assertions."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                has_none_check = False
                for stmt in ast.walk(node):
                    if isinstance(stmt, ast.Compare):
                        for comparator in stmt.comparators:
                            if isinstance(comparator, ast.Constant) and comparator.value is None:
                                has_none_check = True
                
                # Check if function returns Optional but doesn't check
                if node.returns and isinstance(node.returns, ast.Subscript):
                    if hasattr(node.returns.value, 'id') and node.returns.value.id == 'Optional':
                        if not has_none_check:
                            self.findings.append({
                                "id": f"NONE-UNCHECKED-{node.name}",
                                "category": "assertion_checker",
                                "severity": "medium",
                                "title": f"Optional return without None check",
                                "description": f"Function '{node.name}' returns Optional but has no None-safety checks.",
                                "location": f"line {node.lineno}",
                                "confidence": 0.7,
                            })

    def _check_loop_assertions(self, tree: ast.AST, code: str):
        """Check for loop invariant assertions."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                # Check if loop has any assertions
                has_assert = False
                for child in ast.walk(node):
                    if isinstance(child, ast.Assert):
                        has_assert = True
                        break
                
                if not has_assert:
                    # Check complexity - only flag complex loops
                    loop_body_size = len(node.body) if hasattr(node, 'body') else 0
                    if loop_body_size > 3:
                        self.findings.append({
                            "id": f"LOOP-NO-INVARIANT-{node.lineno}",
                            "category": "assertion_checker",
                            "severity": "low",
                            "title": "Loop without invariant assertion",
                            "description": f"Loop at line {node.lineno} has {loop_body_size} statements but no invariant assertions.",
                            "location": f"line {node.lineno}",
                            "suggestion": "Add loop invariant assertions for verification.",
                            "confidence": 0.55,
                        })

    def _check_return_assertions(self, tree: ast.AST, code: str):
        """Check assertions related to return values."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                returns = []
                for child in ast.walk(node):
                    if isinstance(child, ast.Return) and child.value is not None:
                        returns.append(child)
                
                # Check for inconsistent return types
                if len(returns) > 1:
                    # Simple heuristic: check if some return None explicitly
                    has_none_return = any(
                        isinstance(r.value, ast.Constant) and r.value.value is None
                        for r in returns
                    )
                    has_value_return = any(
                        not (isinstance(r.value, ast.Constant) and r.value.value is None)
                        for r in returns
                    )
                    if has_none_return and has_value_return:
                        self.findings.append({
                            "id": f"RETURN-INCONSISTENT-{node.name}",
                            "category": "assertion_checker",
                            "severity": "medium",
                            "title": f"Inconsistent return types in {node.name}",
                            "description": f"Function '{node.name}' sometimes returns a value and sometimes returns None.",
                            "location": f"line {node.lineno}",
                            "confidence": 0.75,
                        })

    def _ast_to_source(self, node: ast.AST, code: str) -> str:
        """Convert AST node to source-like string."""
        try:
            import astor
            return astor.to_source(node).strip()
        except ImportError:
            pass
        
        # Fallback: try to extract from source
        if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
            lines = code.split('\n')
            start = node.lineno - 1
            end = getattr(node, 'end_lineno', node.lineno)
            if start < len(lines):
                return ' '.join(lines[start:end]).strip()
        
        # Last resort: dump the AST
        if isinstance(node, ast.Compare):
            return "<comparison>"
        elif isinstance(node, ast.Call):
            if hasattr(node.func, 'id'):
                return f"{node.func.id}(...)"
            return "<call>"
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Name):
            return node.id
        return f"<{type(node).__name__}>"
