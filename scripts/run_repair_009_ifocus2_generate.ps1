# Repair-009 IntegralityFocus 修复（第二次尝试）- 步骤 2: 候选生成

# 预期耗时: ~9 小时 (预热 ~4h20m + 候选 1-4 秒级 + 候选 5 ~3h + 候选 6 ~2h)

#

# 判决点：候选 6 的 level_set_budget_feasibility 第 3 轮，

# maximum_integrality_violation 对快照闸门 1e-8。

# 上一轮实测 5.030864294042203e-07，当时 IntegralityFocus 未生效。



$ErrorActionPreference = "Stop"

$env:PYTHONUNBUFFERED = "1"

$env:PYTHONDONTWRITEBYTECODE = "1"

$env:PYTHONPATH = (Get-Location).Path



$CONFIG = "configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009.yaml"

$RUNNER = "experiments/run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_009_formal.py"

$PYTHON = "D:\conda_envs\compute\python.exe"

$OUTPUT_ROOT = "results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009_ifocus2"

$LOG_DIR = "results/logs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009_ifocus2"

New-Item -ItemType Directory -Force -Path $LOG_DIR | Out-Null

$LOG = "$LOG_DIR/generate_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"



Write-Host "=== Repair-009 IntegralityFocus 候选生成（第二次） ===" -ForegroundColor Cyan

Write-Host "Config: $CONFIG"

Write-Host "Output: $OUTPUT_ROOT"

Write-Host "Log: $LOG"

Write-Host "预期耗时: ~9 小时"

Write-Host ""



$PREREG = "$OUTPUT_ROOT/preregistration/registration.json"

if (-not (Test-Path $PREREG)) {

    Write-Host "ERROR: Preregistration not found: $PREREG" -ForegroundColor Red

    Write-Host "Run scripts\run_repair_009_ifocus2_prepare.ps1 first" -ForegroundColor Yellow

    exit 1

}



$STRAY = Get-ChildItem "results/tables" -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue

if ($STRAY) {

    Write-Host "ERROR: 已发布结果目录存在 __pycache__，会使 manifest 门失败：" -ForegroundColor Red

    $STRAY | ForEach-Object { Write-Host "  $($_.FullName)" }

    exit 1

}



$content = Get-Content $PREREG -Raw | ConvertFrom-Json

Write-Host "Preregistration:" -ForegroundColor Yellow

Write-Host "  input_contract_sha256 = $($content.input_contract_sha256)"

Write-Host "  IntegralityFocus = $($content.input_contract.formal_successor.solver_options.IntegralityFocus)"

Write-Host ""



Write-Host "Starting generate-candidates at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')..." -ForegroundColor Green

Write-Host ""



& $PYTHON -u $RUNNER --config $CONFIG --stage generate-candidates 2>&1 | Tee-Object -FilePath $LOG



$EXIT_CODE = $LASTEXITCODE

Write-Host ""

Write-Host "=== Generate-candidates completed at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" -ForegroundColor Cyan

Write-Host "Exit code: $EXIT_CODE"

Write-Host "Log saved to: $LOG"



$PROGRESS = Get-ChildItem $LOG_DIR -Directory -ErrorAction SilentlyContinue |

    Sort-Object LastWriteTime -Descending |

    Select-Object -First 1 |

    ForEach-Object { Join-Path $_.FullName "progress.jsonl" }



if ($PROGRESS -and (Test-Path $PROGRESS)) {

    Write-Host ""

    Write-Host "参数是否真的下发给求解器：" -ForegroundColor Yellow

    $applied = Select-String -Path $PROGRESS -Pattern '"IntegralityFocus":\s*1' | Measure-Object

    Write-Host "  effective_solver_options 含 IntegralityFocus=1 的 solve_started 事件数 = $($applied.Count)" -ForegroundColor Cyan

    if ($applied.Count -eq 0) {

        Write-Host "  [ERROR] 参数未出现在任何一次求解中，结果无效" -ForegroundColor Red

    }



    Write-Host ""

    Write-Host "判决类整数违约（level_set 阶段）：" -ForegroundColor Yellow

    Select-String -Path $PROGRESS -Pattern '"maximum_integrality_violation":\s*([0-9.eE+-]+)' -AllMatches |

        ForEach-Object { $_.Matches } |

        ForEach-Object { $_.Groups[1].Value } |

        Where-Object { $_ -ne "null" -and [double]$_ -gt 1e-8 } |

        Sort-Object -Unique |

        ForEach-Object { Write-Host "  violation = $_  (> 1e-8 闸门)" -ForegroundColor Yellow }

}



if ($EXIT_CODE -eq 0) {

    $FRONTIER = "$OUTPUT_ROOT/candidate_frontier/SHA256SUMS"

    if (Test-Path $FRONTIER) {

        $candidates = Get-Content $FRONTIER | Where-Object { $_ -match '\.json$' } | Measure-Object

        Write-Host ""

        Write-Host "[OK] Frontier published, candidate count = $($candidates.Count)" -ForegroundColor Green

    } else {

        Write-Host ""

        Write-Host "[ERROR] Frontier not found: $FRONTIER" -ForegroundColor Red

    }

} else {

    Write-Host ""

    Write-Host "[ERROR] Generate-candidates failed. Check log: $LOG" -ForegroundColor Red

}



exit $EXIT_CODE

