# start-dev.ps1 —— 本地开发模式一键启动 HoneyMOM
#
# 后台启动两个进程（隐藏窗口，不随本脚本退出而结束）：
#   工厂数据回放器（仅本机：MQTT :1883 / OPC UA :4840 / Modbus :5020）
#   HoneyMOM 服务（http://127.0.0.1:8900，演示数据中文；局域网可达）
# 演示账号：admin / honey123
# 日志：data\logs\*.log
# 停止：Get-CimInstance Win32_Process | ? { $_.CommandLine -match 'honeymom|replayer' } | % { Stop-Process -Id $_.ProcessId }
#
# 前置：.venv 已建好（uv），web/dist 已构建（npm ci && npm run build）

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = Join-Path $root '.venv\Scripts\python.exe'

if (-not (Test-Path $py)) {
    Write-Host '缺少 Python 虚拟环境，正在创建并安装依赖……' -ForegroundColor Yellow
    uv venv (Join-Path $root '.venv') --python 3.12
    uv pip install --python $py -r (Join-Path $root 'requirements.txt') -r (Join-Path $root 'replayer\requirements.txt')
}

if (-not (Test-Path (Join-Path $root 'web\dist\index.html'))) {
    Write-Host '缺少前端产物，正在构建……' -ForegroundColor Yellow
    Push-Location (Join-Path $root 'web')
    try { npm ci; npm run build } finally { Pop-Location }
}

$env:MOM_DEMO = '1'
$env:MOM_DEMO_LANG = 'zh'

Write-Host '启动数据回放器（仅本机监听）……' -ForegroundColor Cyan
$logDir = Join-Path $root 'data\logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
Start-Process -FilePath $py -ArgumentList '-m', 'replayer', '--host', '127.0.0.1', '--start', '6', '--speed', '10' `
    -WorkingDirectory $root -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logDir 'replayer.out.log') -RedirectStandardError (Join-Path $logDir 'replayer.err.log')

Start-Sleep -Seconds 2
Write-Host '启动 HoneyMOM……' -ForegroundColor Cyan
Start-Process -FilePath $py -ArgumentList '-m', 'honeymom', 'serve' `
    -WorkingDirectory $root -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logDir 'honeymom.out.log') -RedirectStandardError (Join-Path $logDir 'honeymom.err.log')

Start-Sleep -Seconds 12
Write-Host '打开 http://127.0.0.1:8900 （admin / honey123）' -ForegroundColor Green
Write-Host '局域网访问：http://192.168.1.101:8900' -ForegroundColor Green
Write-Host "日志：$logDir" -ForegroundColor DarkGray
Start-Process 'http://127.0.0.1:8900'
