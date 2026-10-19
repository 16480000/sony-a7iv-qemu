$ErrorActionPreference = 'Stop'
$stateFile = 'D:\CodexWork\sony-a7iv-qemu\menu-a7m4\live-panel.json'

function Get-RunningPanel {
    if (-not (Test-Path -LiteralPath $stateFile)) { return $null }
    try {
        $state = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
        if ($state.url -notmatch '^http://localhost:18764/[A-Za-z0-9_-]+/$') { return $null }
        $null = Invoke-RestMethod -Uri ($state.url + 'status.json') -TimeoutSec 2
        return $state
    } catch { return $null }
}

$panel = Get-RunningPanel
if (-not $panel) {
    $scriptFile = Join-Path $PSScriptRoot 'runtime\native-session.py'
    $linuxScript = (& wsl.exe -d Codex-Z8-Qemu -u root -- wslpath -u $scriptFile).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $linuxScript) { throw '无法访问 Codex-Z8-Qemu 发行版。' }
    $runName = 'menu-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
    $taskProcess = Start-Process -FilePath 'wsl.exe' -WindowStyle Hidden -PassThru -ArgumentList @(
        '-d','Codex-Z8-Qemu','-u','root','--','python3',$linuxScript,
        '--display','none','--web','--keep-menu-awake','--name',$runName
    ) -RedirectStandardOutput (Join-Path $PSScriptRoot 'launcher.log') -RedirectStandardError (Join-Path $PSScriptRoot 'launcher-error.log')
    $deadline = (Get-Date).AddSeconds(100)
    do {
        Start-Sleep -Milliseconds 500
        $panel = Get-RunningPanel
        $taskProcess.Refresh()
        if ($taskProcess.HasExited -and -not $panel) { throw '启动失败，详情见 launcher.log 和 launcher-error.log。' }
    } while (-not $panel -and (Get-Date) -lt $deadline)
    if (-not $panel) { throw '启动超时，详情见 launcher.log。' }
}
Write-Host ('QEMU 原厂实验菜单：' + $panel.url)
Start-Process -FilePath $panel.url
