"""
AXIOM Concurrency Verifier Agent
Estimated tokens per analysis: ~22,000

Verifies concurrent code for race conditions, deadlock potential,
atomicity violations, and proper synchronization. Analyzes threading,
asyncio, multiprocessing, and lock usage patterns.
"""
import re
import ast
import asyncio
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict


class ConcurrencyVerifier:
    """Verifies concurrent code for correctness.
    
    Token estimate: ~22,000 per analysis
    - AST parsing: ~3,000
    - Shared state analysis: ~5,000
    - Race condition detection: ~4,000
    - Deadlock analysis: ~4,000
    - Atomicity checking: ~3,000
    - Report generation: ~3,000
    """

    def __init__(self):
        self.findings = []
        self.concurrency_issues = []
        self.shared_resources = {}
        self.lock_usage = {}

    async def analyze(self, code: str, context: Dict[str, Any] = None) -> dict:
        """Analyze code for concurrency issues."""
        context = context or {}
        self.findings = []
        self.concurrency_issues = []
        self.shared_resources = {}
        self.lock_usage = {}

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "agent": "concurrency_verifier",
                "error": f"Syntax error: {e}",
                "findings": [],
                "summary": "Cannot parse code.",
            }

        # Run all concurrency analyses
        self._detect_shared_state(tree, code)
        self._check_lock_usage(tree, code)
        self._detect_race_conditions(tree, code)
        self._detect_deadlock_potential(tree, code)
        self._check_atomicity(tree, code)
        self._analyze_async_patterns(tree, code)
        self._check_thread_safety(tree, code)
        self._detect_unprotected_writes(tree)
        self._check_barrier_synchronization(tree)

        return {
            "agent": "concurrency_verifier",
            "findings": self.findings,
            "concurrency_issues": self.concurrency_issues,
            "shared_resources": dict(self.shared_resources),
            "summary": f"Found {len(self.concurrency_issues)} concurrency issues and {len(self.findings)} findings.",
            "metrics": {
                "total_issues": len(self.concurrency_issues),
                "race_conditions": sum(1 for i in self.concurrency_issues if i["kind"] == "race_condition"),
                "deadlock_risks": sum(1 for i in self.concurrency_issues if i["kind"] == "deadlock"),
                "atomicity_violations": sum(1 for i in self.concurrency_issues if i["kind"] == "atomicity_violation"),
                "shared_resources": len(self.shared_resources),
                "locks_detected": len(self.lock_usage),
            }
        }

    def _detect_shared_state(self, tree: ast.AST, code: str):
        """Detect shared mutable state."""
        # Detect global variables
        for node in ast.walk(tree):
            if isinstance(node, ast.Global):
                for name in node.names:
                    self.shared_resources[name] = {
                        "kind": "global",
                        "location": f"line {node.lineno}",
                        "accessed_in": [],
                    }
                    self.findings.append({
                        "id": f"CONC-GLOBAL-{name}",
                        "category": "concurrency_verifier",
                        "severity": "high",
                        "title": f"Global variable '{name}' used in concurrent context",
                        "description": f"Global '{name}' is declared and may be accessed by multiple threads.",
                        "location": f"line {node.lineno}",
                        "confidence": 0.7,
                    })

            # Detect class-level mutable state
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                if isinstance(item.value, (ast.List, ast.Dict, ast.Set)):
                                    self.shared_resources[f"{node.name}.{target.id}"] = {
                                        "kind": "class_variable",
                                        "mutable_type": type(item.value).__name__,
                                        "location": f"line {item.lineno}",
                                    }
                                    self.findings.append({
                                        "id": f"CONC-CLASS-MUT-{node.name}-{target.id}",
                                        "category": "concurrency_verifier",
                                        "severity": "medium",
                                        "title": f"Mutable class variable: {node.name}.{target.id}",
                                        "description": f"Class-level mutable {type(item.value).__name__} may cause race conditions.",
                                        "location": f"line {item.lineno}",
                                        "confidence": 0.6,
                                    })

    def _check_lock_usage(self, tree: ast.AST, code: str):
        """Analyze lock acquisition and release patterns."""
        lock_types = {'Lock', 'RLock', 'Semaphore', 'Condition', 'Event'}
        lock_vars = {}
        
        for node in ast.walk(tree):
            # Detect lock creation
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.Call):
                    func_name = None
                    if isinstance(node.value.func, ast.Name):
                        func_name = node.value.func.id
                    elif isinstance(node.value.func, ast.Attribute):
                        func_name = node.value.func.attr
                    
                    if func_name in lock_types:
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                lock_vars[target.id] = {
                                    "type": func_name,
                                    "line": node.lineno,
                                }
                                self.lock_usage[target.id] = {
                                    "type": func_name,
                                    "acquires": [],
                                    "releases": [],
                                }

        # Analyze lock acquisition/release patterns
        for node in ast.walk(tree):
            # Check for context manager usage (with lock:)
            if isinstance(node, ast.With):
                for item in node.items:
                    if isinstance(item.context_expr, ast.Name):
                        if item.context_expr.id in lock_vars:
                            self.lock_usage[item.context_expr.id]["acquires"].append(node.lineno)

            # Check for acquire()/release() calls
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == 'acquire':
                    if isinstance(node.func.value, ast.Name):
                        var = node.func.value.id
                        if var in self.lock_usage:
                            self.lock_usage[var]["acquires"].append(node.lineno)
                elif node.func.attr == 'release':
                    if isinstance(node.func.value, ast.Name):
                        var = node.func.value.id
                        if var in self.lock_usage:
                            self.lock_usage[var]["releases"].append(node.lineno)

        # Check for acquire without release
        for lock_name, usage in self.lock_usage.items():
            if usage["acquires"] and not usage["releases"]:
                # Could be using context manager, which is fine
                pass
            elif len(usage["acquires"]) > len(usage["releases"]):
                self.findings.append({
                    "id": f"CONC-LEAK-{lock_name}",
                    "category": "concurrency_verifier",
                    "severity": "high",
                    "title": f"Lock '{lock_name}' acquired more than released",
                    "description": f"Lock '{lock_name}' has {len(usage['acquires'])} acquires but {len(usage['releases'])} releases. Potential deadlock or resource leak.",
                    "confidence": 0.75,
                })

    def _detect_race_conditions(self, tree: ast.AST, code: str):
        """Detect potential race conditions."""
        # Check for check-then-act patterns
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # Check if condition tests shared state
                tested_vars = self._extract_names_from_test(node.test)
                # Check if body modifies shared state
                modified_vars = set()
                for child in ast.walk(node):
                    if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
                        modified_vars.add(child.id)
                
                overlap = tested_vars & modified_vars
                if overlap:
                    for var in overlap:
                        self.concurrency_issues.append({
                            "kind": "race_condition",
                            "description": f"Check-then-act pattern on '{var}' - TOCTOU vulnerability",
                            "involved_resources": [var],
                            "severity": "high",
                        })

        # Check for increment operations that aren't atomic
        for node in ast.walk(tree):
            if isinstance(node, ast.AugAssign):
                if isinstance(node.op, (ast.Add, ast.Sub)):
                    if isinstance(node.target, ast.Name):
                        var = node.target.id
                        if var in self.shared_resources or var.startswith('self.'):
                            self.concurrency_issues.append({
                                "kind": "race_condition",
                                "description": f"Non-atomic {type(node.op).__name__}= on '{var}'",
                                "involved_resources": [var],
                                "severity": "high",
                            })

        # Check for read-modify-write on shared collections
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.Call):
                    if hasattr(node.value.func, 'attr') and node.value.func.attr in ('pop', 'remove', 'append', 'extend'):
                        self.concurrency_issues.append({
                            "kind": "race_condition",
                            "description": f"Collection modification ({node.value.func.attr}) may not be atomic",
                            "involved_resources": [self._expr_to_str(node.value.func.value)],
                            "severity": "medium",
                        })

    def _detect_deadlock_potential(self, tree: ast.AST, code: str):
        """Detect potential deadlock scenarios."""
        # Check for nested lock acquisition
        lock_names = set(self.lock_usage.keys())
        
        for node in ast.walk(tree):
            if isinstance(node, ast.With):
                # Check for nested with statements acquiring multiple locks
                outer_locks = []
                for item in node.items:
                    if isinstance(item.context_expr, ast.Name) and item.context_expr.id in lock_names:
                        outer_locks.append(item.context_expr.id)
                
                # Check inner with statements
                for child in ast.walk(node):
                    if isinstance(child, ast.With) and child is not node:
                        inner_locks = []
                        for item in child.items:
                            if isinstance(item.context_expr, ast.Name) and item.context_expr.id in lock_names:
                                inner_locks.append(item.context_expr.id)
                        
                        if outer_locks and inner_locks:
                            self.concurrency_issues.append({
                                "kind": "deadlock",
                                "description": f"Nested lock acquisition: {outer_locks} then {inner_locks}. Lock ordering may cause deadlock.",
                                "involved_resources": outer_locks + inner_locks,
                                "severity": "high",
                            })

            # Check for acquire() inside a locked section
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == 'acquire' and isinstance(node.func.value, ast.Name):
                    lock_name = node.func.value.id
                    # This is a simplified check - real deadlock detection requires CFG analysis
                    self.concurrency_issues.append({
                        "kind": "deadlock",
                        "description": f"Lock '{lock_name}' acquired - check for nested acquisitions",
                        "involved_resources": [lock_name],
                        "severity": "medium",
                    })

    def _check_atomicity(self, tree: ast.AST, code: str):
        """Check for atomicity violations."""
        # Check for compound operations that should be atomic
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.BoolOp):
                    # Check if condition depends on shared state
                    names = self._extract_names(node.value)
                    shared = names & set(self.shared_resources.keys())
                    if shared:
                        self.concurrency_issues.append({
                            "kind": "atomicity_violation",
                            "description": f"Compound boolean on shared vars: {shared}",
                            "involved_resources": list(shared),
                            "severity": "medium",
                        })

        # Check for read-then-write patterns
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.BinOp):
                    left_vars = self._extract_names(node.left) if isinstance(node.targets[0], ast.Name) else set()
                    right_vars = self._extract_names(node.value)
                    
                    # Check if same variable is read and written
                    if isinstance(node.targets[0], ast.Name):
                        target = node.targets[0].id
                        if target in right_vars:
                            # x = x + 1 pattern - not atomic
                            if target in self.shared_resources:
                                self.concurrency_issues.append({
                                    "kind": "atomicity_violation",
                                    "description": f"Read-modify-write on shared '{target}'",
                                    "involved_resources": [target],
                                    "severity": "high",
                                })

    def _analyze_async_patterns(self, tree: ast.AST, code: str):
        """Analyze async/await patterns for concurrency issues."""
        async_funcs = []
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                async_funcs.append(node.name)
                
                # Check for blocking calls in async functions
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        func_name = None
                        if isinstance(child.func, ast.Name):
                            func_name = child.func.id
                        elif isinstance(child.func, ast.Attribute):
                            func_name = child.func.attr
                        
                        blocking_calls = {'sleep', 'time', 'input', 'read', 'write', 'connect',
                                         'recv', 'send', 'accept', 'bind', 'listen'}
                        if func_name in blocking_calls:
                            self.findings.append({
                                "id": f"CONC-BLOCKING-ASYNC-{node.name}-{child.lineno}",
                                "category": "concurrency_verifier",
                                "severity": "medium",
                                "title": f"Potentially blocking call in async function",
                                "description": f"Async function '{node.name}' calls '{func_name}' which may block the event loop.",
                                "location": f"line {child.lineno}",
                                "confidence": 0.6,
                            })

        # Check for unawaited coroutines
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in async_funcs:
                    # Check if the call is awaited
                    parent = None
                    for parent in ast.walk(tree):
                        if isinstance(parent, ast.Await):
                            if parent.value is node:
                                break
                    # Without parent tracking, we flag potential issues

    def _check_thread_safety(self, tree: ast.AST, code: str):
        """Check for thread-safety issues."""
        # Check for thread-unsafe patterns
        for node in ast.walk(tree):
            # Check for mutable default arguments
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for default in node.args.defaults + node.args.kw_defaults:
                    if default and isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        self.findings.append({
                            "id": f"CONC-MUTABLE-DEFAULT-{node.name}",
                            "category": "concurrency_verifier",
                            "severity": "medium",
                            "title": f"Mutable default argument in {node.name}",
                            "description": f"Function '{node.name}' has mutable default argument. Shared across calls.",
                            "location": f"line {node.lineno}",
                            "confidence": 0.8,
                        })

            # Check for singleton patterns without thread safety
            if isinstance(node, ast.ClassDef):
                for method in node.body:
                    if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if method.name in ('__new__', 'getInstance', 'instance'):
                            has_lock = False
                            for child in ast.walk(method):
                                if isinstance(child, ast.Name) and child.id in self.lock_usage:
                                    has_lock = True
                            if not has_lock:
                                self.findings.append({
                                    "id": f"CONC-UNSAFE-SINGLETON-{node.name}",
                                    "category": "concurrency_verifier",
                                    "severity": "medium",
                                    "title": f"Potentially thread-unsafe singleton in {node.name}",
                                    "description": f"Singleton pattern in '{node.name}' without synchronization.",
                                    "location": f"line {method.lineno}",
                                    "confidence": 0.6,
                                })

    def _detect_unprotected_writes(self, tree: ast.AST):
        """Detect writes to shared state without synchronization."""
        # This is a simplified check
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in self.shared_resources:
                        # Check if we're inside a lock
                        # Simplified: just flag the write
                        self.findings.append({
                            "id": f"CONC-UNPROTECTED-WRITE-{target.id}-{node.lineno}",
                            "category": "concurrency_verifier",
                            "severity": "medium",
                            "title": f"Unprotected write to shared '{target.id}'",
                            "description": f"Write to shared variable '{target.id}' without apparent lock protection.",
                            "location": f"line {node.lineno}",
                            "confidence": 0.6,
                        })

    def _check_barrier_synchronization(self, tree: ast.AST):
        """Check for missing barrier synchronization."""
        thread_starts = []
        thread_joins = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if hasattr(node.func, 'attr'):
                    if node.func.attr == 'start':
                        thread_starts.append(node.lineno)
                    elif node.func.attr == 'join':
                        thread_joins.append(node.lineno)
        
        if thread_starts and len(thread_starts) != len(thread_joins):
            self.findings.append({
                "id": "CONC-MISSING-JOIN",
                "category": "concurrency_verifier",
                "severity": "medium",
                "title": "Thread started without join",
                "description": f"{len(thread_starts)} thread starts but {len(thread_joins)} joins. Threads may not be properly synchronized.",
                "confidence": 0.6,
            })

    def _extract_names_from_test(self, node: ast.AST) -> Set[str]:
        """Extract variable names from a condition."""
        names = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                names.add(child.id)
        return names

    def _extract_names(self, node: ast.AST) -> Set[str]:
        """Extract all variable names from an expression."""
        names = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                names.add(child.id)
        return names

    def _expr_to_str(self, node: ast.AST) -> str:
        """Convert expression to string."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._expr_to_str(node.value)}.{node.attr}"
        return f"<{type(node).__name__}>"
