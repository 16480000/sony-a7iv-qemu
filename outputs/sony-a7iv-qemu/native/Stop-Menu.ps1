$ErrorActionPreference = 'Stop'
$stateFile = 'D:\CodexWork\sony-a7iv-qemu\menu-a7m4\live-panel.json'
$panel = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
if ($panel.url -notmatch '^http://localhost:18764/[A-Za-z0-9_-]+/$') { throw '本地面板地址格式不符。' }
$null = Invoke-RestMethod -Uri ($panel.url + 'action') -Method Post -ContentType 'application/json' -Body '{"key":"STOP"}' -TimeoutSec 25
Write-Host '已请求停止本任务的 QEMU 虚拟机。'
