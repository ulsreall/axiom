"""
AXIOM Web Dashboard - Flask application for the Formal Code Verification Platform.
"""
import asyncio
import json
import hashlib
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from core.orchestrator import Orchestrator
from core.config import Config

app = Flask(__name__)
config = Config()
orchestrator = Orchestrator()

# Sample data for startup
SAMPLE_DATA = {
    "recent_analyses": [
        {
            "id": "vrf-a1b2c3d4-1716300000",
            "timestamp": "2026-05-21T04:00:00",
            "language": "python",
            "findings": 3,
            "status": "PASS_WITH_WARNINGS",
            "duration_ms": 1250.5,
            "confidence": 0.87,
        },
        {
            "id": "vrf-e5f6g7h8-1716300100",
            "timestamp": "2026-05-21T04:01:40",
            "language": "python",
            "findings": 0,
            "status": "PASS",
            "duration_ms": 980.2,
            "confidence": 0.95,
        },
        {
            "id": "vrf-i9j0k1l2-1716300200",
            "timestamp": "2026-05-21T04:03:20",
            "language": "python",
            "findings": 7,
            "status": "NEEDS_REVIEW",
            "duration_ms": 2100.8,
            "confidence": 0.72,
        },
    ],
    "token_stats": {
        "daily_total": 2_450_000,
        "daily_limit": 82_000_000,
        "agents": {
            "assertion_checker": {"total": 320000, "calls": 16},
            "logic_analyzer": {"total": 352000, "calls": 16},
            "invariant_detector": {"total": 288000, "calls": 16},
            "proof_generator": {"total": 400000, "calls": 16},
            "boundary_analyzer": {"total": 256000, "calls": 16},
            "concurrency_verifier": {"total": 352000, "calls": 16},
            "specification_validator": {"total": 288000, "calls": 16},
            "termination_prover": {"total": 256000, "calls": 16},
            "abstract_interpreter": {"total": 320000, "calls": 16},
            "verification_report": {"total": 224000, "calls": 16},
        }
    }
}

SAMPLE_CODE = '''def binary_search(arr, target):
    """Search for target in sorted array."""
    left, right = 0, len(arr) - 1
    assert left <= right + 1, "Invalid initial bounds"
    
    while left <= right:
        mid = (left + right) // 2
        assert left <= mid <= right, "mid out of bounds"
        
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    
    return -1


def factorial(n):
    """Compute factorial recursively."""
    assert isinstance(n, int), "n must be integer"
    if n < 0:
        raise ValueError("n must be non-negative")
    if n <= 1:
        return 1
    return n * factorial(n - 1)


class BankAccount:
    """Simple bank account with balance tracking."""
    
    def __init__(self, initial_balance=0):
        assert initial_balance >= 0, "Balance cannot be negative"
        self._balance = initial_balance
        self._transactions = []
    
    def deposit(self, amount):
        assert amount > 0, "Deposit must be positive"
        self._balance += amount
        self._transactions.append(('deposit', amount))
    
    def withdraw(self, amount):
        assert amount > 0, "Withdrawal must be positive"
        assert amount <= self._balance, "Insufficient funds"
        self._balance -= amount
        self._transactions.append(('withdraw', amount))
    
    @property
    def balance(self):
        return self._balance
'''


@app.route('/')
def index():
    return render_template('index.html', sample_code=SAMPLE_CODE)


@app.route('/api/verify', methods=['POST'])
def verify():
    data = request.json
    code = data.get('code', '')
    language = data.get('language', 'python')
    agents = data.get('agents', None)
    
    if not code:
        return jsonify({"error": "No code provided"}), 400
    
    loop = asyncio.new_event_loop()
    try:
        report = loop.run_until_complete(
            orchestrator.verify(code, language=language, agents=agents)
        )
        # Convert report to dict
        result = {
            "id": report.id,
            "timestamp": report.timestamp,
            "language": report.language,
            "overall_status": report.overall_status.value,
            "confidence_score": report.confidence_score,
            "total_findings": report.total_findings,
            "findings": [
                {
                    "id": f.id,
                    "category": f.category,
                    "severity": f.severity.value,
                    "title": f.title,
                    "description": f.description,
                    "location": f.location,
                    "suggestion": f.suggestion,
                    "confidence": f.confidence,
                }
                for f in report.findings
            ],
            "agent_results": {
                k: {kk: vv for kk, vv in v.items() if kk != 'error'} if isinstance(v, dict) else str(v)
                for k, v in report.agent_results.items()
            },
            "token_usage": report.token_usage,
            "duration_ms": report.analysis_duration_ms,
        }
        return jsonify(result)
    finally:
        loop.close()


@app.route('/api/status')
def status():
    status = orchestrator.get_status()
    status["recent_analyses"] = SAMPLE_DATA["recent_analyses"]
    return jsonify(status)


@app.route('/api/token-stats')
def token_stats():
    stats = orchestrator.token_tracker.get_usage_summary()
    return jsonify(stats)


@app.route('/api/health')
def health():
    return jsonify({
        "status": "healthy",
        "service": "AXIOM",
        "version": "1.0.0",
        "agents_loaded": len(orchestrator._agents),
        "uptime": "running",
    })


if __name__ == '__main__':
    print(f"AXIOM Verification Platform starting on port {config.PORT}")
    print(f"Dashboard: http://localhost:{config.PORT}")
    app.run(host='0.0.0.0', port=config.PORT, debug=config.DEBUG)
