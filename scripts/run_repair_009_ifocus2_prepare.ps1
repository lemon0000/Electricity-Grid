# Repair-009 IntegralityFocus 修复（第二次尝试）- 步骤 1: 预注册

# 预期耗时: ~4.5 小时

#

# 与第一次尝试的差别：IntegralityFocus 现在真的会到达 Gurobi。

# 第一次尝试把参数写进 formal_solver.solver.options，但 gurobi_runtime_options

# 与 FormalCgModelAdapter._call_config 两层都不读该键，参数被静默丢弃，

# 5 小时 59 分的运行没有测试到声明的参数。作废记录见

# results/tables/..._repair_009_ifocus/invalidation/invalidation.json



$ErrorActionPreference = "Stop"

$env:PYTHONUNBUFFERED = "1"

# 防止动态导入冻结 benchmark 模块时在已发布结果目录写入 __pycache__，

# 那会让该目录文件集偏离 SHA256SUMS，使下一次启动的 _verify_manifest 失败。

$env:PYTHONDONTWRITEBYTECODE = "1"

# 仓库未安装为包，runner 用 `from experiments import ...` 绝对导入，

# 因此必须把仓库根显式放进 PYTHONPATH，否则启动即 ModuleNotFoundError。

$env:PYTHONPATH = (Get-Location).Path



$CONFIG = "configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009.yaml"

$RUNNER = "experiments/run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_009_formal.py"

$PYTHON = "D:\conda_envs\compute\python.exe"

$OUTPUT_ROOT = "results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009_ifocus2"

$LOG_DIR = "results/logs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009_ifocus2"

New-Item -ItemType Directory -Force -Path $LOG_DIR | Out-Null

$LOG = "$LOG_DIR/prepare_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"



Write-Host "=== Repair-009 IntegralityFocus 预注册（第二次） ===" -ForegroundColor Cyan

Write-Host "Config: $CONFIG"

Write-Host "Output: $OUTPUT_ROOT"

Write-Host "Log: $LOG"

Write-Host "预期耗时: ~4.5 小时"

Write-Host ""



if (-not (Test-Path $CONFIG)) {

    Write-Host "ERROR: Config not found: $CONFIG" -ForegroundColor Red

    exit 1

}

if (-not (Test-Path $RUNNER)) {

    Write-Host "ERROR: Runner not found: $RUNNER" -ForegroundColor Red

    exit 1

}



if (Test-Path $OUTPUT_ROOT) {

    $items = Get-ChildItem $OUTPUT_ROOT -ErrorAction SilentlyContinue

    if ($items) {

        Write-Host "ERROR: Output directory not empty: $OUTPUT_ROOT" -ForegroundColor Red

        Write-Host "Contains: $($items.Count) items"

        exit 1

    }

}



# 上一轮的教训：跑到候选 5 会在已发布的 warmstart benchmark 目录写入 .pyc，

# 使下一次启动的 manifest 门失败。启动前先确认没有残留。

$STRAY = Get-ChildItem "results/tables" -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue

if ($STRAY) {

    Write-Host "ERROR: 已发布结果目录存在 __pycache__，会使 manifest 门失败：" -ForegroundColor Red

    $STRAY | ForEach-Object { Write-Host "  $($_.FullName)" }

    Write-Host "删除后重试。" -ForegroundColor Yellow

    exit 1

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



    $PREREG = "$OUTPUT_ROOT/preregistration/registration.json"

    if (Test-Path $PREREG) {

        Write-Host "[OK] Preregistration published" -ForegroundColor Green



        $content = Get-Content $PREREG -Raw | ConvertFrom-Json

        $ifocus = $content.input_contract.formal_successor.solver_options.IntegralityFocus

        if ($ifocus -eq 1) {

            Write-Host "[OK] IntegralityFocus = $ifocus" -ForegroundColor Green

        } else {

            Write-Host "[WARN] IntegralityFocus = $ifocus (expected 1)" -ForegroundColor Yellow

        }



        Write-Host "[INFO] input_contract_sha256 = $($content.input_contract_sha256)" -ForegroundColor Cyan

    } else {

        Write-Host "[ERROR] Preregistration not found: $PREREG" -ForegroundColor Red

    }



    Write-Host ""

    Write-Host "Next step: run scripts\run_repair_009_ifocus2_generate.ps1" -ForegroundColor Cyan

} else {

    Write-Host ""

    Write-Host "[ERROR] Prepare failed. Check log: $LOG" -ForegroundColor Red

}



exit $EXIT_CODE

