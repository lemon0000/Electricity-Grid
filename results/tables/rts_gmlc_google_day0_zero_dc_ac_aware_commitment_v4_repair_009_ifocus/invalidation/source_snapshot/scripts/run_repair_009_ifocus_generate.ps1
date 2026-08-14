# Repair-009 IntegralityFocus 修复 - 步骤 2: 候选生成
# 预期耗时: ~9 小时 (预热 4h + 候选 1-4 秒级 + 候选 5 3h + 候选 6 2h)

$ErrorActionPreference = "Stop"
$env:PYTHONUNBUFFERED = "1"

$CONFIG = "configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009.yaml"
$RUNNER = "experiments/run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_009_formal.py"
$PYTHON = "D:\conda_envs\compute\python.exe"
$LOG = "repair_009_ifocus_generate_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

Write-Host "=== Repair-009 IntegralityFocus 候选生成 ===" -ForegroundColor Cyan
Write-Host "Config: $CONFIG"
Write-Host "Output: results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009_ifocus"
Write-Host "Log: $LOG"
Write-Host "预期耗时: ~9 小时"
Write-Host ""

# 验证预注册存在
$OUTPUT_ROOT = "results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009_ifocus"
$PREREG = "$OUTPUT_ROOT/preregistration/registration.json"
if (-not (Test-Path $PREREG)) {
    Write-Host "ERROR: Preregistration not found: $PREREG" -ForegroundColor Red
    Write-Host "Run scripts\run_repair_009_ifocus_prepare.ps1 first" -ForegroundColor Yellow
    exit 1
}

# 显示预注册信息
$content = Get-Content $PREREG -Raw | ConvertFrom-Json
$contract_hash = $content.input_contract_sha256
$ifocus = $content.input_contract.formal_successor.solver_options.IntegralityFocus
Write-Host "Preregistration:" -ForegroundColor Yellow
Write-Host "  input_contract_sha256 = $contract_hash"
Write-Host "  IntegralityFocus = $ifocus"
Write-Host ""

Write-Host "Starting generate-candidates at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')..." -ForegroundColor Green
Write-Host ""

& $PYTHON -u $RUNNER --config $CONFIG --stage generate-candidates 2>&1 | Tee-Object -FilePath $LOG

$EXIT_CODE = $LASTEXITCODE
Write-Host ""
Write-Host "=== Generate-candidates completed at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" -ForegroundColor Cyan
Write-Host "Exit code: $EXIT_CODE"
Write-Host "Log saved to: $LOG"

if ($EXIT_CODE -eq 0) {
    Write-Host ""
    Write-Host "Verification..." -ForegroundColor Yellow

    # 验证前沿发布
    $FRONTIER = "$OUTPUT_ROOT/candidate_frontier/SHA256SUMS"
    if (Test-Path $FRONTIER) {
        Write-Host "[OK] Frontier published" -ForegroundColor Green

        # 统计候选数
        $candidates = Get-Content $FRONTIER | Where-Object { $_ -match '\.json$' } | Measure-Object
        Write-Host "[INFO] Candidate count = $($candidates.Count)" -ForegroundColor Cyan

        # 检查候选 6
        $cand6 = Get-Content $FRONTIER | Where-Object { $_ -match 'candidate_00006\.json' }
        if ($cand6) {
            Write-Host "[OK] Candidate 6 present in frontier" -ForegroundColor Green
        } else {
            Write-Host "[WARN] Candidate 6 not found in frontier" -ForegroundColor Yellow
        }
    } else {
        Write-Host "[ERROR] Frontier not found: $FRONTIER" -ForegroundColor Red
    }

    # 检查 progress.jsonl 中的判决
    $LOG_DIR = Get-ChildItem "results/logs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009_ifocus" -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($LOG_DIR) {
        $PROGRESS = "$($LOG_DIR.FullName)/progress.jsonl"
        if (Test-Path $PROGRESS) {
            Write-Host ""
            Write-Host "Checking integrality violations in progress.jsonl..." -ForegroundColor Yellow

            $violations = Get-Content $PROGRESS | Where-Object { $_ -match 'maximum_integrality_violation' }
            $failed_checks = $violations | Where-Object { $_ -match '"maximum_integrality_violation":\s*[^0]' -and $_ -notmatch '"maximum_integrality_violation":\s*null' }

            if ($failed_checks) {
                Write-Host "[INFO] Found integrality violations:" -ForegroundColor Cyan
                $failed_checks | ForEach-Object {
                    if ($_ -match '"maximum_integrality_violation":\s*([0-9.e-]+)') {
                        $val = $Matches[1]
                        Write-Host "  violation = $val" -ForegroundColor Yellow
                    }
                }
            } else {
                Write-Host "[OK] No integrality violations detected (all pass 1e-8)" -ForegroundColor Green
            }
        }
    }

    Write-Host ""
    Write-Host "Next step: inspect $OUTPUT_ROOT/candidate_frontier/" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "[ERROR] Generate-candidates failed. Check log: $LOG" -ForegroundColor Red
}

exit $EXIT_CODE
