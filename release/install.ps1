# MO 平衡补丁 v1.0.0 — 安装脚本
# 目标：把 _internal\rulesmo.ini 复制到 MO 3.3.6 游戏目录，实现外置覆盖。
# 安全：不修改任何 .mix/.exe；安装前自动备份已有同名文件；安装后校验 SHA256。

param(
    [switch]$DryRun,
    [string]$GameDir = ""
)

# 扫描阶段需要宽松，关键操作再自行 try/catch + 事后校验
$ErrorActionPreference = "Continue"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$internal = $PSScriptRoot
$pkgRoot  = Split-Path -Parent $internal
$payload  = Join-Path $internal "rulesmo.ini"

function Line { Write-Host ("-" * 58) -ForegroundColor DarkGray }
function Ok($m)   { Write-Host ("  [OK]   " + $m) -ForegroundColor Green }
function Info($m) { Write-Host ("  [..]   " + $m) -ForegroundColor Gray }
function Warn($m) { Write-Host ("  [!!]   " + $m) -ForegroundColor Yellow }
function Die($m)  { Write-Host ""; Write-Host ("  [失败] " + $m) -ForegroundColor Red; Write-Host ""; exit 1 }

Line
Write-Host "  MO 3.3.6 平衡补丁 v1.0.0 — 安装" -ForegroundColor Cyan
Write-Host "  Mental Omega 3.3.6 Balance Patch - Install" -ForegroundColor DarkGray
Line
Write-Host ""

# ---------- 1. 检查自身完整性 ----------
if (-not (Test-Path -LiteralPath $payload)) {
    Die "缺少 _internal\rulesmo.ini。请勿把文件从文件夹里单独拖出来，请整包解压后双击。"
}
$payHash = ""
try { $payHash = (Get-FileHash -LiteralPath $payload -Algorithm SHA256).Hash } catch { Die "无法读取补丁文件（可能被杀毒软件拦截）。" }
$paySize = (Get-Item -LiteralPath $payload).Length
Info ("补丁文件: " + $paySize.ToString("N0") + " 字节  SHA256 " + $payHash.Substring(0,16) + "...")

# ---------- 2. 定位游戏目录 ----------
function Test-GameDir([string]$p) {
    if ([string]::IsNullOrWhiteSpace($p)) { return $false }
    try {
        if (-not (Test-Path -LiteralPath $p)) { return $false }
        if (-not (Test-Path -LiteralPath (Join-Path $p "gamemd.exe"))) { return $false }
        return (Test-Path -LiteralPath (Join-Path $p "expandmo99.mix"))
    } catch { return $false }
}

$cand = New-Object System.Collections.Generic.List[string]
if ($GameDir)        { $cand.Add($GameDir) }
if ($env:MO_GAMEDIR) { $cand.Add($env:MO_GAMEDIR) }
$cand.Add($pkgRoot)
$parentOfPkg = Split-Path -Parent $pkgRoot
if ($parentOfPkg) { $cand.Add($parentOfPkg) }

# 只枚举**真实存在**的驱动器，避免 Join-Path 对不存在盘符抛异常
$drives = @()
try { $drives = @(Get-PSDrive -PSProvider FileSystem -ErrorAction SilentlyContinue | ForEach-Object { $_.Root }) } catch { $drives = @() }

$folderNames = @("Mental Omega","MentalOmega","Mental Omega 3.3.6","心灵终结","MO","RA2MO")
foreach ($r in $drives) {
    foreach ($n in $folderNames) {
        try { $cand.Add((Join-Path $r $n)) } catch {}
    }
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
    Write-Host "  未能自动定位游戏目录（需要同时含 gamemd.exe 和 expandmo99.mix）。" -ForegroundColor Yellow
    Write-Host "  请把游戏文件夹拖到本窗口，或直接输入完整路径后按回车：" -ForegroundColor Yellow
    $inp = Read-Host "  游戏目录"
    $inp = $inp.Trim().Trim('"').Trim("'")
    if (-not (Test-GameDir $inp)) {
        Die "该目录不像 MO 3.3.6 安装目录：未找到 gamemd.exe 或 expandmo99.mix。"
    }
    try { $found = (Resolve-Path -LiteralPath $inp).Path.TrimEnd('\') } catch { $found = $inp.TrimEnd('\') }
}
Ok ("游戏目录: " + $found)

# ---------- 3. 版本校验 ----------
$mixPath = Join-Path $found "expandmo99.mix"
$mix = $null
try { $mix = Get-Item -LiteralPath $mixPath } catch { Die "无法读取 expandmo99.mix。" }
$expectMixSize = 11004015
if ($mix.Length -eq $expectMixSize) {
    Ok "版本校验: expandmo99.mix 大小符合 MO 3.3.6"
} else {
    Warn ("expandmo99.mix 大小 " + $mix.Length.ToString("N0") + "，本补丁针对 3.3.6（" + $expectMixSize.ToString("N0") + "）。")
    Warn "若不是 3.3.6，平衡数值可能对不上。"
    $yn = Read-Host "  仍要继续安装吗？输入 y 继续，其它任意键退出"
    if ($yn -ne "y" -and $yn -ne "Y") { Write-Host "  已取消。"; exit 0 }
}

# ---------- 4. 检查游戏是否在运行 ----------
$running = Get-Process -Name "gamemd","MentalOmegaClient" -ErrorAction SilentlyContinue
if ($running) {
    Die "游戏正在运行（gamemd / MentalOmegaClient）。请完全退出游戏后再双击安装。"
}
Ok "游戏未运行"

# ---------- 5. 备份 + 安装 ----------
$target = Join-Path $found "rulesmo.ini"
$stamp  = Get-Date -Format "yyyyMMdd_HHmmss"
$notes  = New-Object System.Collections.Generic.List[string]

# DryRun 必须在任何写入动作之前退出
if ($DryRun) {
    Write-Host ""
    if (Test-Path -LiteralPath $target) {
        $h = ""
        try { $h = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash } catch {}
        if ($h -eq $payHash) { Info "游戏目录中已是本补丁版本（哈希一致）" }
        else { Info "游戏目录中存在其它 rulesmo.ini，正式安装会先备份它" }
    } else {
        Info "游戏目录中没有 rulesmo.ini（首次安装）"
    }
    Warn "DryRun 模式：只检查不写入。正式运行会写入："
    Write-Host ("         " + $target)
    Write-Host ""
    Line
    Ok "预检查全部通过（未做任何修改）"
    Line
    exit 0
}

if (Test-Path -LiteralPath $target) {
    $oldHash = ""
    try { $oldHash = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash } catch {}
    if ($oldHash -eq $payHash) {
        Info "游戏目录里已经是本补丁的版本（哈希一致），无需再备份"
        $notes.Add("安装前已有本补丁版本，哈希一致，未新增备份")
    } else {
        $bak = "rulesmo.ini.bak_" + $stamp
        try {
            Copy-Item -LiteralPath $target -Destination (Join-Path $found $bak) -Force
            Ok ("已备份原有 rulesmo.ini -> " + $bak)
            $notes.Add("已备份原有规则文件 -> " + $bak + "  SHA256 " + $oldHash)
        } catch {
            Die ("备份失败，已中止（未做任何修改）：" + $_.Exception.Message)
        }
    }
} else {
    Info "游戏目录原本没有 rulesmo.ini（首次安装，原版规则在 MIX 内未被修改）"
    $notes.Add("安装前不存在 rulesmo.ini（首次安装）")
}

try {
    Copy-Item -LiteralPath $payload -Destination $target -Force
} catch {
    Die ("写入失败：" + $_.Exception.Message + "`n        如果游戏装在 Program Files 下，请右键这个 bat -> 以管理员身份运行。")
}

$newHash = ""
try { $newHash = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash } catch {}
if ($newHash -ne $payHash) { Die "安装后校验失败（哈希不一致），请重新解压补丁包再试。" }
Ok "安装后 SHA256 校验一致"

# ---------- 6. 写日志 ----------
$logPath = Join-Path $found "MO平衡补丁_安装记录.txt"
try {
    $log = @()
    $log += "MO 3.3.6 平衡补丁 v1.0.0"
    $log += "时间: " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    $log += "游戏目录: " + $found
    $log += "补丁 SHA256: " + $payHash
    foreach ($n in $notes) { $log += $n }
    $log += ""
    $log += "回滚方法: 双击本包里的「恢复原版.bat」"
    $log | Set-Content -LiteralPath $logPath -Encoding UTF8
} catch {}

Write-Host ""
Line
Write-Host "  安装完成！" -ForegroundColor Green
Write-Host ""
Write-Host "  进游戏后可以核对（造价最直观）：" -ForegroundColor Cyan
Write-Host "    光棱坦克 1050 / 雷神炮艇 1500 / 铁骑兵 350" -ForegroundColor White
Write-Host "    长枪战士视野 15 / 火控穹顶可造 3 个" -ForegroundColor White
Write-Host ""
Write-Host "  想还原原版：双击同目录下的「恢复原版.bat」" -ForegroundColor Cyan
Line
Write-Host ""
