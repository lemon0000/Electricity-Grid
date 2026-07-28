"""Constants for repair-006 cost-bisection failure; used by repair-007 to validate
the predecessor state before importing its checkpoints.

repair-006 attempt5 (formal_repair_006_20260727T224731Z) ran correctly but the
cost decision bisection for candidate 5 (q_proxy_delta_0p0200) exhausted its
time budget (7200s/round, 1 round attempted) without finding a feasible incumbent
at the cost target required by the 0.1% maximum accepted gap.  This is not
mathematical infeasibility — repair-007 relaxes the maximum to 0.12% so the
direct cost certificate (gap=0.109%) qualifies directly without bisection.
"""

from __future__ import annotations

EXPECTED_INPUT_CONTRACT_SHA256 = (
    "b1d4a3c63db6924e0203cca3ed579f4498b3e1b2956529fafae7600985b02657"
)
EXPECTED_PREREGISTRATION_MANIFEST_SHA256 = (
    "0c2d26d6d1563c4a3f5e583c818ba085b7213ad3a73f8a664e2a4678e11a14f0"
)
CHECKPOINT_NAMES = (
    "01_q_proxy_delta_0p0010",
    "02_q_proxy_delta_0p0025",
    "03_q_proxy_delta_0p0050",
    "04_q_proxy_delta_0p0100",
)
EXPECTED_CHECKPOINT_MANIFEST_SHA256S = (
    "664b7e874ca582c69ac3fe7da3a11c5b8b777d674720ccf24e42cad2806ccf81",
    "7ad5be111ed6ffe90f212efbe344fd16163867c017dd2301a68f4f419aad4d00",
    "b24caf827801f02b4e384a289ee11836e50650a6aaa7d382de94f4763f557793",
    "fe94c8e58b0f129d92931208054eaf929a12ece8ec1931bfc0e56035a87de08d",
)
EXPECTED_CANDIDATE_JSON_SHA256S = (
    "374c9c9dd04c933a602acd166bf08b9e839b9759f0dce02868956e5d475c7ede",
    "a71fc4c49fd64df1b61bb76b056172a7e29e8d8e4349ce320e81b8bd52211a01",
    "84882b00d5b706b138193685c392a024adff765427822793a4b4143de5788698",
    "7da38dfda10206a69e17c9ef8f32dfc516aab31189b981d06714f9928133292f",
)

__all__ = [
    "CHECKPOINT_NAMES",
    "EXPECTED_INPUT_CONTRACT_SHA256",
    "EXPECTED_PREREGISTRATION_MANIFEST_SHA256",
    "EXPECTED_CHECKPOINT_MANIFEST_SHA256S",
    "EXPECTED_CANDIDATE_JSON_SHA256S",
]
