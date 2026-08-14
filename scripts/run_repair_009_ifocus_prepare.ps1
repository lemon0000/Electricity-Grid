# Repair-009 IntegralityFocus 修复 - 步骤 1: 预注册
# 预期耗时: ~4.5 小时

$ErrorActionPreference = "Stop"
$env:PYTHONUNBUFFERED = "1"

$CONFIG = "configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009.yaml"
$RUNNER = "experiments/run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_009_formal.py"
$PYTHON = "D:\conda_envs\compute\python.exe"
$LOG = "repair_009_ifocus_prepare_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

Write-Host "=== Repair-009 IntegralityFocus 预注册 ===" -ForegroundColor Cyan
Write-Host "Config: $CONFIG"
Write-Host "Output: results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009_ifocus"
Write-Host "Log: $LOG"
Write-Host "预期耗时: ~4.5 小时"
Write-Host ""

# 验证文件存在
if (-not (Test-Path $CONFIG)) {
    Write-Host "ERROR: Config not found: $CONFIG" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $RUNNER)) {
    Write-Host "ERROR: Runner not found: $RUNNER" -ForegroundColor Red
    exit 1
}

# 验证新 output_directory 不存在或为空
$OUTPUT_ROOT = "results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009_ifocus"
if (Test-Path $OUTPUT_ROOT) {
    $items = Get-ChildItem $OUTPUT_ROOT -ErrorAction SilentlyContinue
    if ($items) {
        Write-Host "ERROR: Output directory not empty: $OUTPUT_ROOT" -ForegroundColor Red
        Write-Host "Contains: $($items.Count) items"
        exit 1
    }
}

Write-Host "Starting prepare at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')..." -ForegroundColor Green
Write-Host ""

& $PYTHON -u $RUNNER --config $CONFIG --stage prepare 2>&1 | Tee-Object -FilePath $LOG

$EXIT_CODE = $LASTEXITCODE
Write-Host ""
Write-Host "=== Prepare completed at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" -ForegroundColor Cyan
Write-Host "Exit code: $EXIT_CODE"
Write-Host "Log saved to: $LOG"

if ($EXIT_CODE -eq 0) {
    Write-Host ""
    Write-Host "Verification..." -ForegroundColor Yellow

    # 验证预注册发布
    $PREREG = "$OUTPUT_ROOT/preregistration/registration.json"
    if (Test-Path $PREREG) {
        Write-Host "[OK] Preregistration published" -ForegroundColor Green

        # 验证 IntegralityFocus
        $content = Get-Content $PREREG -Raw | ConvertFrom-Json
        $ifocus = $content.input_contract.formal_successor.solver_options.IntegralityFocus
        if ($ifocus -eq 1) {
            Write-Host "[OK] IntegralityFocus = $ifocus" -ForegroundColor Green
        } else {
            Write-Host "[WARN] IntegralityFocus = $ifocus (expected 1)" -ForegroundColor Yellow
        }

        # 显示 input_contract_sha256
        $contract_hash = $content.input_contract_sha256
        Write-Host "[INFO] input_contract_sha256 = $contract_hash" -ForegroundColor Cyan
    } else {
        Write-Host "[ERROR] Preregistration not found: $PREREG" -ForegroundColor Red
    }

    Write-Host ""
    Write-Host "Next step: run scripts\run_repair_009_ifocus_generate.ps1" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "[ERROR] Prepare failed. Check log: $LOG" -ForegroundColor Red
}

exit $EXIT_CODE
