#!/usr/bin/env bash
# repair-009: preregistration -> (on success) launch formal solve.
# Single detached chain so the solve starts without further intervention.
set -u
cd "D:/CUHKSZ/Research Project/electricity-grid" || exit 1

CFG="configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009.yaml"
LOG="repair009_chain.log"
PY="D:/conda_envs/compute/python.exe"

stamp() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
say() { echo "[$(stamp)] $*" >> "$LOG"; }

say "CHAIN_START"
say "STEP1_PREREG_BEGIN"

"$PY" -u -B -m experiments.run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_009_formal \
    --config "$CFG" --stage prepare >> "$LOG" 2>&1
rc=$?

if [ $rc -ne 0 ]; then
    say "STEP1_PREREG_FAILED rc=$rc"
    say "CHAIN_ABORT"
    exit $rc
fi

say "STEP1_PREREG_OK"
say "STEP2_LAUNCH_SOLVE_BEGIN"

ATTEMPT="formal_repair_009_$(date -u +%Y%m%dT%H%M%SZ)"
say "attempt_id=$ATTEMPT"

nohup "$PY" -u -B -m experiments.run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_009_formal \
    --config "$CFG" --stage generate-candidates --attempt-id "$ATTEMPT" \
    >> repair009_solve.log 2>&1 &
solve_pid=$!
disown 2>/dev/null

say "STEP2_SOLVE_LAUNCHED pid=$solve_pid attempt=$ATTEMPT"
say "CHAIN_DONE"
exit 0
