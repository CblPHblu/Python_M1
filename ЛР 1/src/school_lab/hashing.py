from dataclasses import asdict
import hashlib
import json
from .models import Submission

def stable_hash(value: object) -> str:
    canonical = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def submission_hash(submission: Submission) -> str:
    return stable_hash(asdict(submission))
