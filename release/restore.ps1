# MO 平衡补丁 v1.0.0 — 恢复原版脚本
# 目标：删除覆盖用 rulesmo.ini；若安装前备份过原文件，则还原备份。
# 说明：MIX 内的原版规则文件从未被修改，删掉覆盖文件即恢复原版。

param(
    [switch]$DryRun,
    [string]$GameDir = ""
)

# 扫描阶段需要宽松，关键操作再自行 try/catch + 事后校验
$ErrorActionPreference = "Continue"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

function Line { Write-Host ("-" * 58) -ForegroundColor DarkGray }
function Ok($m)   { Write-Host ("  [OK]   " + $m) -ForegroundColor Green }
function Info($m) { Write-Host ("  [..]   " + $m) -ForegroundColor Gray }
function Warn($m) { Write-Host ("  [!!]   " + $m) -ForegroundColor Yellow }
function Die($m)  { Write-Host ""; Write-Host ("  [失败] " + $m) -ForegroundColor Red; Write-Host ""; exit 1 }

Line
Write-Host "  MO 3.3.6 平衡补丁 v1.0.0 — 恢复原版" -ForegroundColor Cyan
Write-Host "  Restore to vanilla" -ForegroundColor DarkGray
Line
Write-Host ""

function Test-GameDir([string]$p) {
    if ([string]::IsNullOrWhiteSpace($p)) { return $false }
    try {
        if (-not (Test-Path -LiteralPath $p)) { return $false }
        return (Test-Path -LiteralPath (Join-Path $p "gamemd.exe"))
    } catch { return $false }
}

$pkgRoot = Split-Path -Parent $PSScriptRoot
$cand = New-Object System.Collections.Generic.List[string]
if ($GameDir)        { $cand.Add($GameDir) }
if ($env:MO_GAMEDIR) { $cand.Add($env:MO_GAMEDIR) }
$cand.Add($pkgRoot)
$parentOfPkg = Split-Path -Parent $pkgRoot
if ($parentOfPkg) { $cand.Add($parentOfPkg) }

# 只枚举**真实存在**的驱动器
$drives = @()
try { $drives = @(Get-PSDrive -PSProvider FileSystem -ErrorAction SilentlyContinue | ForEach-Object { $_.Root }) } catch { $drives = @() }

$folderNames = @("Mental Omega","MentalOmega","Mental Omega 3.3.6","心灵终结","MO","RA2MO")
foreach ($r in $drives) {
    foreach ($n in $folderNames) { try { $cand.Add((Join-Path $r $n)) } catch {} }
    foreach ($sub in @("Games\Mental Omega","Program Files\Mental Omega","Program Files (x86)\Mental Omega","MO")) {
        try { $cand.Add((Join-Path $r $sub)) } catch {}
    }
}
$cand = @($cand | Where-Object { $_ } | Select-Object -Unique)

$found = $null
foreach ($c in $cand) {
    if (Test-GameDir $c) {
        try { $found = (Resolve-Path -LiteralPath $c).Path.TrimEnd('\') } catch { $found = $c.TrimEnd('\') }
        break
    }
}
if (-not $found) {
    Write-Host "  未能自动定位游戏目录。" -ForegroundColor Yellow
    $inp = Read-Host "  请输入 MO 3.3.6 游戏目录（含 gamemd.exe）"
    $inp = $inp.Trim().Trim('"').Trim("'")
    if (-not (Test-GameDir $inp)) { Die "该目录下没有 gamemd.exe，可能不是游戏目录。" }
    try { $found = (Resolve-Path -LiteralPath $inp).Path.TrimEnd('\') } catch { $found = $inp.TrimEnd('\') }
}
Ok ("游戏目录: " + $found)

$running = Get-Process -Name "gamemd","MentalOmegaClient" -ErrorAction SilentlyContinue
if ($running) { Die "游戏正在运行，请完全退出后再恢复。" }
Ok "游戏未运行"

$target = Join-Path $found "rulesmo.ini"
$baks = @()
try {
    $baks = @(Get-ChildItem -LiteralPath $found -Filter "rulesmo.ini.bak_*" -File -ErrorAction SilentlyContinue |
              Sort-Object LastWriteTime -Descending)
} catch { $baks = @() }

if ((-not (Test-Path -LiteralPath $target)) -and $baks.Count -eq 0) {
    Write-Host ""
    Ok "当前没有覆盖文件，已经是原版状态，无需恢复。"
    Write-Host ""
    exit 0
}

if ($DryRun) {
    Warn "DryRun 模式：只检查不写入。"
    if ($baks.Count -gt 0) { Info ("将还原备份: " + $baks[0].Name) } else { Info "将删除 rulesmo.ini" }
    exit 0
}

if ($baks.Count -gt 0) {
    $bak = $baks[0]
    try {
        Copy-Item -LiteralPath $bak.FullName -Destination $target -Force
    } catch {
        Die ("还原备份失败：" + $_.Exception.Message + "`n        如果游戏装在 Program Files 下，请右键这个 bat -> 以管理员身份运行。")
    }
    Ok ("已还原安装前的规则文件: " + $bak.Name)
    Remove-Item -LiteralPath $bak.FullName -Force -ErrorAction SilentlyContinue
    Info "已移除该备份文件（内容已还原到位）"
} else {
    try {
        Remove-Item -LiteralPath $target -Force
    } catch {
        Die ("删除失败：" + $_.Exception.Message + "`n        如果游戏装在 Program Files 下，请右键这个 bat -> 以管理员身份运行。")
    }
    Ok "已删除覆盖文件 rulesmo.ini"
}

if (Test-Path -LiteralPath $target) {
    Ok "恢复后目录中存在 rulesmo.ini（为安装前备份的内容）"
} else {
    Ok "恢复后目录中无 rulesmo.ini —— 即完全原版状态"
}

$logPath = Join-Path $found "MO平衡补丁_安装记录.txt"
if (Test-Path -LiteralPath $logPath) {
    try { Add-Content -LiteralPath $logPath -Value ("`r`n恢复原版于 " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss")) -Encoding UTF8 } catch {}
}

Write-Host ""
Line
Write-Host "  已恢复原版，可以正常启动游戏。" -ForegroundColor Green
Line
Write-Host ""
