"""
AXIOM Specification Validator Agent
Estimated tokens per analysis: ~18,000

Validates code against specifications, behavior contracts, and expected
interfaces. Checks spec compliance, interface conformance, and behavior matching.
"""
import re
import ast
import asyncio
from typing import Dict, List, Any, Optional, Set


class SpecificationValidator:
    """Validates code against specifications and contracts.
    
    Token estimate: ~18,000 per analysis
    - AST parsing: ~3,000
    - Interface conformance: ~4,000
    - Spec compliance checking: ~4,000
    - Behavior matching: ~3,000
    - Contract validation: ~2,000
    - Report generation: ~2,000
    """

    def __init__(self):
        self.findings = []
        self.violations = []

    async def analyze(self, code: str, context: Dict[str, Any] = None) -> dict:
        """Validate code against specifications."""
        context = context or {}
        self.findings = []
        self.violations = []
        specification = context.get("specification", "")

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "agent": "specification_validator",
                "error": f"Syntax error: {e}",
                "findings": [],
                "summary": "Cannot parse code.",
            }

        # Run all validation checks
        self._validate_interfaces(tree, code)
        self._check_abstract_method_implementation(tree, code)
        self._validate_naming_conventions(tree, code)
        self._check_docstring_completeness(tree, code)
        self._validate_error_handling(tree, code)
        self._check_return_value_usage(tree, code)
        self._validate_side_effects(tree, code)
        self._check_api_consistency(tree, code)
        if specification:
            self._validate_against_spec(tree, code, specification)

        return {
            "agent": "specification_validator",
            "findings": self.findings,
            "violations": self.violations,
            "summary": f"Found {len(self.violations)} violations and {len(self.findings)} findings.",
            "metrics": {
                "total_violations": len(self.violations),
                "interface_issues": sum(1 for v in self.violations if v.get("kind") == "interface"),
                "naming_issues": sum(1 for v in self.violations if v.get("kind") == "naming"),
                "docstring_issues": sum(1 for v in self.violations if v.get("kind") == "documentation"),
                "error_handling_issues": sum(1 for v in self.violations if v.get("kind") == "error_handling"),
                "compliance_score": self._compute_compliance_score(),
            }
        }

    def _validate_interfaces(self, tree: ast.AST, code: str):
        """Validate interface conformance."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name
                
                # Check for __init__ method
                has_init = False
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == '__init__':
                        has_init = True
                        break
                
                # Check for expected dunder methods based on usage patterns
                methods = {item.name for item in node.body 
                          if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))}
                
                # If class has __eq__ but not __hash__
                if '__eq__' in methods and '__hash__' not in methods:
                    self.violations.append({
                        "kind": "interface",
                        "description": f"Class '{class_name}' defines __eq__ but not __hash__. Instances won't be hashable.",
                        "location": f"class {class_name}",
                        "severity": "medium",
                    })

                # If class has __iter__ but not __next__
                if '__iter__' in methods and '__next__' not in methods:
                    self.violations.append({
                        "kind": "interface",
                        "description": f"Class '{class_name}' defines __iter__ but not __next__. May not be a proper iterator.",
                        "location": f"class {class_name}",
                        "severity": "medium",
                    })

                # Check for __str__ without __repr__
                if '__str__' in methods and '__repr__' not in methods:
                    self.findings.append({
                        "id": f"SPEC-NO-REPR-{class_name}",
                        "category": "specification_validator",
                        "severity": "info",
                        "title": f"Missing __repr__ in {class_name}",
                        "description": f"Class has __str__ but not __repr__. Consider adding __repr__ for debugging.",
                        "confidence": 0.7,
                    })

    def _check_abstract_method_implementation(self, tree: ast.AST, code: str):
        """Check that abstract methods are properly implemented."""
        # Find abstract base classes
        abc_classes = {}
        concrete_classes = {}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                is_abstract = False
                abstract_methods = set()
                
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id in ('ABC', 'Protocol'):
                        is_abstract = True
                
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        for dec in item.decorator_list:
                            if isinstance(dec, ast.Name) and dec.id == 'abstractmethod':
                                abstract_methods.add(item.name)
                                is_abstract = True
                
                if is_abstract:
                    abc_classes[node.name] = {
                        "methods": abstract_methods,
                        "bases": [b.id if isinstance(b, ast.Name) else str(b) for b in node.bases],
                    }
                else:
                    concrete_classes[node.name] = {
                        "methods": {item.name for item in node.body 
                                   if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))},
                        "bases": [b.id if isinstance(b, ast.Name) else str(b) for b in node.bases],
                    }

        # Check concrete classes implement abstract methods
        for class_name, info in concrete_classes.items():
            for base_name in info["bases"]:
                if base_name in abc_classes:
                    missing = abc_classes[base_name]["methods"] - info["methods"]
                    if missing:
                        self.violations.append({
                            "kind": "interface",
                            "description": f"'{class_name}' doesn't implement abstract methods from '{base_name}': {', '.join(missing)}",
                            "location": f"class {class_name}",
                            "severity": "high",
                        })

    def _validate_naming_conventions(self, tree: ast.AST, code: str):
        """Check naming convention compliance."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Classes should be CamelCase
                if not node.name[0].isupper():
                    self.violations.append({
                        "kind": "naming",
                        "description": f"Class '{node.name}' should start with uppercase (CamelCase).",
                        "location": f"line {node.lineno}",
                        "severity": "low",
                    })

                # Check for single underscore prefix on private attrs
                for item in node.body:
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                name = target.id
                                if (name.startswith('__') and not name.startswith('___') and 
                                    not name.endswith('__')):
                                    self.findings.append({
                                        "id": f"SPEC-NAME-MANGLE-{node.name}-{name}",
                                        "category": "specification_validator",
                                        "severity": "low",
                                        "title": f"Name mangling: {name}",
                                        "description": f"Attribute '{name}' uses double underscore prefix which triggers name mangling.",
                                        "confidence": 0.8,
                                    })

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Functions should be snake_case
                name = node.name
                if not name.startswith('__') and '_' not in name and len(name) > 1:
                    if name != name.lower() and not name[0].isupper():
                        self.findings.append({
                            "id": f"SPEC-NAME-FUNC-{name}",
                            "category": "specification_validator",
                            "severity": "info",
                            "title": f"Non-snake_case function: {name}",
                            "description": f"Function '{name}' doesn't follow snake_case convention.",
                            "location": f"line {node.lineno}",
                            "confidence": 0.6,
                        })

                # Check for single-letter parameter names (except common ones)
                acceptable_single = {'i', 'j', 'k', 'x', 'y', 'z', 'n', 'e', 'f', 'a', 'b'}
                for arg in node.args.args:
                    if arg.arg == 'self':
                        continue
                    if len(arg.arg) == 1 and arg.arg not in acceptable_single:
                        self.findings.append({
                            "id": f"SPEC-NAME-PARAM-{node.name}-{arg.arg}",
                            "category": "specification_validator",
                            "severity": "info",
                            "title": f"Single-letter parameter: {arg.arg}",
                            "description": f"Parameter '{arg.arg}' in '{node.name}' has a non-descriptive single-letter name.",
                            "location": f"line {node.lineno}",
                            "confidence": 0.5,
                        })

    def _check_docstring_completeness(self, tree: ast.AST, code: str):
        """Check docstring presence and completeness."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_name = node.name
                if func_name.startswith('_'):
                    continue
                
                has_docstring = (node.body and isinstance(node.body[0], ast.Expr) and 
                                isinstance(node.body[0].value, ast.Constant) and
                                isinstance(node.body[0].value.value, str))
                
                if not has_docstring:
                    self.violations.append({
                        "kind": "documentation",
                        "description": f"Function '{func_name}' lacks docstring.",
                        "location": f"line {node.lineno}",
                        "severity": "low",
                    })
                else:
                    docstring = node.body[0].value.value
                    # Check for parameter documentation
                    params = [arg.arg for arg in node.args.args if arg.arg != 'self']
                    for param in params:
                        if param not in docstring and f":param {param}" not in docstring:
                            self.violations.append({
                                "kind": "documentation",
                                "description": f"Parameter '{param}' not documented in '{func_name}'.",
                                "location": f"line {node.lineno}",
                                "severity": "low",
                            })

            elif isinstance(node, ast.ClassDef):
                has_docstring = (node.body and isinstance(node.body[0], ast.Expr) and 
                                isinstance(node.body[0].value, ast.Constant))
                if not has_docstring:
                    self.violations.append({
                        "kind": "documentation",
                        "description": f"Class '{node.name}' lacks docstring.",
                        "location": f"line {node.lineno}",
                        "severity": "low",
                    })

    def _validate_error_handling(self, tree: ast.AST, code: str):
        """Validate error handling patterns."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                # Check for bare except
                for handler in node.handlers:
                    if handler.type is None:
                        self.violations.append({
                            "kind": "error_handling",
                            "description": "Bare except clause catches all exceptions including SystemExit and KeyboardInterrupt.",
                            "location": f"line {handler.lineno}",
                            "severity": "high",
                        })
                    elif isinstance(handler.type, ast.Name) and handler.type.id == 'Exception':
                        # Check if handler body just passes
                        if (len(handler.body) == 1 and isinstance(handler.body[0], ast.Pass)):
                            self.violations.append({
                                "kind": "error_handling",
                                "description": "Exception silently swallowed (except Exception: pass).",
                                "location": f"line {handler.lineno}",
                                "severity": "high",
                            })

                # Check for try without finally or except
                if not node.handlers and not node.finalbody:
                    self.violations.append({
                        "kind": "error_handling",
                        "description": "Try block without except or finally.",
                        "location": f"line {node.lineno}",
                        "severity": "medium",
                    })

    def _check_return_value_usage(self, tree: ast.AST, code: str):
        """Check for unused return values."""
        void_functions = {'print', 'append', 'extend', 'insert', 'remove', 'sort', 'clear', 'update'}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                if isinstance(node.value.func, ast.Name):
                    func_name = node.value.func.id
                    if func_name not in void_functions and not func_name.startswith('_'):
                        self.findings.append({
                            "id": f"SPEC-UNUSED-RET-{func_name}-{node.lineno}",
                            "category": "specification_validator",
                            "severity": "low",
                            "title": f"Return value of {func_name}() discarded",
                            "description": f"Line {node.lineno}: Return value of '{func_name}()' is not used.",
                            "location": f"line {node.lineno}",
                            "confidence": 0.5,
                        })

    def _validate_side_effects(self, tree: ast.AST, code: str):
        """Check for unexpected side effects in functions."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith(('get', 'is_', 'has_', 'check', 'find', 'search')):
                    # These functions should not have side effects
                    has_side_effect = False
                    for child in ast.walk(node):
                        if isinstance(child, ast.Call):
                            if isinstance(child.func, ast.Name) and child.func.id == 'print':
                                has_side_effect = True
                            elif hasattr(child.func, 'attr') and child.func.attr in ('write', 'append', 'insert', 'remove', 'delete', 'update'):
                                has_side_effect = True
                    
                    if has_side_effect:
                        self.findings.append({
                            "id": f"SPEC-SIDE-EFFECT-{node.name}",
                            "category": "specification_validator",
                            "severity": "medium",
                            "title": f"Side effect in query function '{node.name}'",
                            "description": f"Function '{node.name}' appears to be a query but has side effects.",
                            "location": f"line {node.lineno}",
                            "confidence": 0.7,
                        })

    def _check_api_consistency(self, tree: ast.AST, code: str):
        """Check for consistent API patterns within a class."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = {}
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods[item.name] = {
                            "args": [a.arg for a in item.args.args if a.arg != 'self'],
                            "returns": item.returns is not None,
                        }
                
                # Check for inconsistent return patterns
                non_init = {k: v for k, v in methods.items() if not k.startswith('__')}
                if non_init:
                    returns_some = sum(1 for v in non_init.values() if v["returns"])
                    returns_none = sum(1 for v in non_init.values() if not v["returns"])
                    if returns_some > 0 and returns_none > 0:
                        self.findings.append({
                            "id": f"SPEC-INCONSISTENT-RETURNS-{node.name}",
                            "category": "specification_validator",
                            "severity": "low",
                            "title": f"Inconsistent return annotations in {node.name}",
                            "description": f"Class '{node.name}' has mixed return type annotations ({returns_some} annotated, {returns_none} not).",
                            "confidence": 0.6,
                        })

    def _validate_against_spec(self, tree: ast.AST, code: str, specification: str):
        """Validate code against provided specification."""
        spec_lines = specification.lower().split('\n')
        
        # Extract required functions from spec
        required_funcs = set()
        for line in spec_lines:
            if 'function' in line or 'method' in line or 'def ' in line:
                # Try to extract function names
                words = line.split()
                for i, word in enumerate(words):
                    if word in ('function', 'method', 'def') and i + 1 < len(words):
                        name = words[i+1].strip('():,')
                        required_funcs.add(name)
        
        # Check if code implements required functions
        actual_funcs = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                actual_funcs.add(node.name)
        
        for func in required_funcs:
            if func not in actual_funcs:
                self.violations.append({
                    "kind": "spec_compliance",
                    "description": f"Required function '{func}' from specification not found in code.",
                    "severity": "high",
                })

    def _compute_compliance_score(self) -> float:
        """Compute overall compliance score."""
        if not self.violations:
            return 1.0
        
        severity_weights = {"critical": 0.4, "high": 0.3, "medium": 0.2, "low": 0.1}
        total_weight = sum(severity_weights.get(v.get("severity", "low"), 0.1) for v in self.violations)
        max_deductions = len(self.violations) * 0.4  # Max possible deduction
        
        return max(0.0, 1.0 - (total_weight / max(max_deductions, 1)))
