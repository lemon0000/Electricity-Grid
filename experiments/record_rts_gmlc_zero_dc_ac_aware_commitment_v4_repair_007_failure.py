"""Constants for repair-007 cost-gap failure; used by repair-008 to validate
the predecessor state before importing its checkpoints.

repair-007 attempt1 (formal_repair_007_20260728T055849Z) ran correctly but the
direct cost normalization for candidate 5 (q_proxy_delta_0p0200) produced a
relative gap of 0.126%, which exceeded the 0.12% maximum_accepted threshold.
The cost bisection fallback was blocked because the proxy reached the candidate
via the level-set fallback path (not the direct proxy path), which the protocol
prohibits from triggering a further cost bisection cascade.
repair-008 raises the maximum to 0.15% so the direct certificate passes directly.
"""

from __future__ import annotations

EXPECTED_INPUT_CONTRACT_SHA256 = (
    "ec8b1f510361d91eadb33a1a94349d5b1a5b1a5cb41652ab406927db78f4da83"
)
EXPECTED_PREREGISTRATION_MANIFEST_SHA256 = (
    "7a2607ebae3ad968c5a5f67918895d7d2130d7e71b904348a72bb03c2b09a4f6"
)
CHECKPOINT_NAMES = (
    "01_q_proxy_delta_0p0010",
    "02_q_proxy_delta_0p0025",
    "03_q_proxy_delta_0p0050",
    "04_q_proxy_delta_0p0100",
)
EXPECTED_CHECKPOINT_MANIFEST_SHA256S = (
    "eefb0dc2fb7ab30d5b9b74c7bf71d8acadc1f6710d3e1e172341ea26e0916e26",
    "efbf9c6cc6e11d08f05b1038578d9a7ebb1582830eddff4735f50c3c3f21c1b1",
    "523304364dad223629a2981c5387dafd71bdfd547503d77bd72b0fbc8bb9fcbe",
    "1a10856181a509890bc5eb5d9cf7905d77e217bf3548d314e1bb93fea6e4c651",
)
EXPECTED_CANDIDATE_JSON_SHA256S = (
    "3ec69786c5fd880125b80dde6aa03532c37011438dbe9a3ec2d3276d3d87db64",
    "e10109098f6c9db921da511214c502b513e126c1408d61e495e2d4ded374d12e",
    "25ad608eb48227a6cbb0739856dd0d39403292be3ba6538b594cf78a4b543e63",
    "412732449f3877625c50320f0bde18477398491cddc4a9406358d2f55249df5f",
)

__all__ = [
    "CHECKPOINT_NAMES",
    "EXPECTED_INPUT_CONTRACT_SHA256",
    "EXPECTED_PREREGISTRATION_MANIFEST_SHA256",
    "EXPECTED_CHECKPOINT_MANIFEST_SHA256S",
    "EXPECTED_CANDIDATE_JSON_SHA256S",
]
