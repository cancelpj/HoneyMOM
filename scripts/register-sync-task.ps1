<#
    register-sync-task.ps1 —— 把「同步上游」注册成 Windows 计划任务（每天定时跑）

    用法：
      pwsh scripts\register-sync-task.ps1              # 默认每天 09:00
      pwsh scripts\register-sync-task.ps1 -Time 20:30  # 换成别的时间
      pwsh scripts\register-sync-task.ps1 -Unregister  # 删除计划任务

    说明：以当前登录用户身份运行（不需要管理员密码），机器开机且该用户已登录时才会执行。
#>
[CmdletBinding()]
param(
    [string]$Time = '09:00',
    [switch]$Unregister,
    [string]$TaskName = 'HoneyMOM-upstream-sync'
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$sync = Join-Path $repo 'scripts\sync-upstream.ps1'

if ($Unregister) {
    & schtasks /delete /tn $TaskName /f | Out-Null
    if ($LASTEXITCODE -eq 0) { Write-Host "已删除计划任务：$TaskName" -ForegroundColor Green }
    else { Write-Host "计划任务不存在或删除失败：$TaskName" -ForegroundColor Yellow }
    exit 0
}

if (-not (Test-Path $sync)) { throw "找不到 $sync" }

$pwsh = (Get-Command pwsh -ErrorAction SilentlyContinue)?.Source
if (-not $pwsh) { $pwsh = 'C:\Program Files\PowerShell\7\pwsh.exe' }
$tr = "`"$pwsh`" -NoProfile -ExecutionPolicy Bypass -File `"$sync`" -Push"

Write-Host "注册计划任务：$TaskName" -ForegroundColor Cyan
Write-Host "  命令：$tr" -ForegroundColor DarkGray
Write-Host "  时间：每天 $Time" -ForegroundColor DarkGray

& schtasks /create /tn $TaskName /tr $tr /sc daily /st $Time /f | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host '创建失败（可能需要管理员权限）。请用管理员身份重开 PowerShell 再执行本脚本。' -ForegroundColor Red
    exit 1
}
Write-Host "已创建。现在查看：schtasks /query /tn $TaskName" -ForegroundColor Green
Write-Host "手动跑一次：schtasks /run /tn $TaskName" -ForegroundColor DarkGray
