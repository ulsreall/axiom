"""
AXIOM Core - Formal Code Verification Platform
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Central configuration for AXIOM."""
    PORT = int(os.getenv("AXIOM_PORT", 8083))
    DEBUG = os.getenv("AXIOM_DEBUG", "false").lower() == "true"
    PROOF_DIR = os.getenv("AXIOM_PROOF_DIR", "./proof")
    LOG_LEVEL = os.getenv("AXIOM_LOG_LEVEL", "INFO")
    MAX_TOKENS_PER_DAY = int(os.getenv("AXIOM_MAX_TOKENS_PER_DAY", 82000000))

    AGENT_TIMEOUT = 120
    MAX_CODE_LENGTH = 100000
    SUPPORTED_LANGUAGES = ["python", "c", "cpp", "java", "rust", "go"]

    # Agent token budget estimates (per analysis)
    AGENT_TOKEN_ESTIMATES = {
        "assertion_checker": 20000,
        "logic_analyzer": 22000,
        "invariant_detector": 18000,
        "proof_generator": 25000,
        "boundary_analyzer": 16000,
        "concurrency_verifier": 22000,
        "specification_validator": 18000,
        "termination_prover": 16000,
        "abstract_interpreter": 20000,
        "verification_report": 14000,
    }
