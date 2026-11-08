# 一键启动：MySQL（未运行则启动）→（可选）重建数据 → 启动 Flask 应用
# 用法：start.bat           直接启动
#       start.bat -Reset   重建数据库并导入演示数据
# 若 5000 端口已被占用，会提示：1=关闭占用进程并继续，2=退出
param(
    [switch]$Reset
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

# ===== 本机路径与数据库密码，换机器时只改这里 =====
$MysqlDir = 'C:\xampp\mysql\bin'
$MysqlIni = 'C:\xampp\mysql\bin\my.ini'
$DbPassword = '123456'
$Python = 'C:\Users\1\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'

Set-Location $Root

function Test-Port($port) {
    Test-NetConnection 127.0.0.1 -Port $port -InformationLevel Quiet -WarningAction SilentlyContinue
}

# ---------- 1. MySQL ----------
if (Test-Port 3306) {
    Write-Host '[1/3] MySQL 已在运行，跳过启动' -ForegroundColor Green
}
else {
    Write-Host '[1/3] 正在启动 MySQL ...' -ForegroundColor Cyan
    Start-Process -FilePath (Join-Path $MysqlDir 'mysqld.exe') `
        -ArgumentList @("--defaults-file=$MysqlIni", '--console') -WindowStyle Minimized
    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        if (Test-Port 3306) { $ready = $true; break }
    }
    if (-not $ready) {
        Write-Host 'MySQL 启动失败：请检查 3306 端口是否被占用' -ForegroundColor Red
        exit 1
    }
    Write-Host '      MySQL 已就绪' -ForegroundColor Green
}

# ---------- 2. 数据库 ----------
if ($Reset) {
    Write-Host '[2/3] 重建数据库并导入初始数据 ...' -ForegroundColor Cyan
    # 直接用文件作为标准输入，避免 PowerShell 管道改写字符编码
    $MysqlExe = Join-Path $MysqlDir 'mysql.exe'
    $SqlFile = Join-Path $Root 'init.sql'
    $proc = Start-Process -FilePath $MysqlExe -NoNewWindow -Wait -PassThru `
        -ArgumentList @('--default-character-set=utf8mb4', '-u', 'root', "--password=$DbPassword") `
        -RedirectStandardInput $SqlFile
    if ($proc.ExitCode -ne 0) {
        Write-Host '数据导入失败：请确认脚本顶部的 $DbPassword 与本机 MySQL root 密码一致' -ForegroundColor Red
        exit 1
    }
    Write-Host '      导入完成' -ForegroundColor Green
}
else {
    Write-Host '[2/3] 跳过数据导入（需要重建请运行 start.bat -Reset）' -ForegroundColor Yellow
}

# ---------- 3. 应用 ----------
if (Test-Port 5000) {
    Write-Host '[3/3] 5000 端口已被占用' -ForegroundColor Yellow
    $owners = @(Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique)
    foreach ($ownerPid in $owners) {
        $proc = Get-Process -Id $ownerPid -ErrorAction SilentlyContinue
        if ($proc) { Write-Host ("      占用进程：{0}（PID {1}）" -f $proc.ProcessName, $ownerPid) }
        else { Write-Host ("      占用进程：PID {0}" -f $ownerPid) }
    }
    Write-Host '      1) 关闭该进程并继续启动'
    Write-Host '      2) 直接退出'
    do { $choice = Read-Host '请选择 [1/2]' } while ($choice -ne '1' -and $choice -ne '2')
    if ($choice -eq '2') {
        Write-Host '已退出' -ForegroundColor Yellow
        exit 1
    }
    foreach ($ownerPid in $owners) {
        Stop-Process -Id $ownerPid -Force -ErrorAction SilentlyContinue
    }
    for ($i = 0; $i -lt 10; $i++) {
        Start-Sleep -Milliseconds 500
        if (-not (Test-Port 5000)) { break }
    }
    if (Test-Port 5000) {
        Write-Host '端口仍被占用，无法启动' -ForegroundColor Red
        exit 1
    }
    Write-Host '      端口已释放' -ForegroundColor Green
}
if (-not (Test-Path $Python)) { $Python = 'python' }

Write-Host '[3/3] 启动应用，浏览器将自动打开；按 Ctrl+C 停止' -ForegroundColor Cyan
Start-Job -ScriptBlock { Start-Sleep -Seconds 4; Start-Process 'http://127.0.0.1:5000' } | Out-Null
& $Python app.py
