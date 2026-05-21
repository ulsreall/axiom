```
 █████╗ ██╗  ██╗██╗ ██████╗ ███╗   ███╗
██╔══██╗╚██╗██╔╝██║██╔═══██╗████╗ ████║
███████║ ╚███╔╝ ██║██║   ██║██╔████╔██║
██╔══██║ ██╔██╗ ██║██║   ██║██║╚██╔╝██║
██║  ██║██╔╝ ██╗██║╚██████╔╝██║ ╚═╝ ██║
╚═╝  ╚═╝╚═╝  ╚═╝╚═╝ ╚═════╝ ╚═╝     ╚═╝
```

# AXIOM — Formal Code Verification Platform

Multi-agent formal verification platform deploying 10 specialized AI agents for proving code correctness and logical soundness.

## Architecture

```
Codebase → [Verification Pipeline] → Proof Report
    ├─ Assertion Checker (20K tok)
    ├─ Logic Analyzer (22K tok)
    ├─ Invariant Detector (18K tok)
    ├─ Proof Generator (25K tok)
    ├─ Boundary Analyzer (16K tok)
    ├─ Concurrency Verifier (22K tok)
    ├─ Specification Validator (18K tok)
    ├─ Termination Prover (16K tok)
    ├─ Abstract Interpreter (20K tok)
    └─ Verification Report (14K tok)
```

## Token Consumption

| Agent | Tokens/Scan | Scans/Day | Daily Total |
|-------|-------------|-----------|-------------|
| Proof Generator | 25K | 600 | 15.0M |
| Logic Analyzer | 22K | 550 | 12.1M |
| Concurrency Verifier | 22K | 500 | 11.0M |
| Assertion Checker | 20K | 500 | 10.0M |
| Abstract Interpreter | 20K | 450 | 9.0M |
| Invariant Detector | 18K | 450 | 8.1M |
| Spec Validator | 18K | 400 | 7.2M |
| Boundary Analyzer | 16K | 400 | 6.4M |
| Termination Prover | 16K | 350 | 5.6M |
| Verification Report | 14K | 350 | 4.9M |
| **Total** | **191K** | | **89.3M/day** |

## Installation

```bash
pip install -r requirements.txt
cp .env.example .env
```

## Usage

```bash
# CLI
python cli.py verify ./src
python cli.py agents
python cli.py stats

# Web Dashboard
python web/app.py  # http://localhost:8083
```

## License

MIT
