$ErrorActionPreference = 'Stop'
$stateFile = 'D:\CodexWork\sony-a7iv-qemu\menu-a7m4\live-panel.json'
function Get-CameraPanel {
    if (-not (Test-Path -LiteralPath $stateFile)) { return $null }
    try {
        $state = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
        if ($state.url -notmatch '^http://localhost:18764/[A-Za-z0-9_-]+/$') { return $null }
        $null = Invoke-RestMethod -Uri ($state.url + 'status.json') -TimeoutSec 2
        return $state
    } catch { return $null }
}
$panel = Get-CameraPanel
if (-not $panel) {
    $image = 'D:\CodexWork\sony-a7iv-qemu\menu-a7m4\main-virtual-card-stable.cpio'
    if ((Get-FileHash -LiteralPath $image -Algorithm SHA256).Hash -ne 'EF7ED4046BCD3CCC0EA42F03550A958459272FB134AC61FAC6F7A734F2A304D4') {
        throw '主界面镜像与已验证版本不同，停止启动。'
    }
    $sourceFile = Join-Path $PSScriptRoot 'runtime\native-session.py'
    $linuxScript = (& wsl.exe -d Codex-Z8-Qemu -u root -- wslpath -u $sourceFile).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $linuxScript) { throw '无法访问 Codex-Z8-Qemu。' }
    $runName = 'camera-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
    $launcher = Start-Process -FilePath 'wsl.exe' -WindowStyle Hidden -PassThru -ArgumentList @(
        '-d','Codex-Z8-Qemu','-u','root','--','python3',$linuxScript,
        '--display','none','--web','--auto-main','--card-main','--initramfs','main-virtual-card-stable.cpio',
        '--name',$runName
    ) -RedirectStandardOutput (Join-Path $PSScriptRoot 'camera-launcher.log') -RedirectStandardError (Join-Path $PSScriptRoot 'camera-launcher-error.log')
    $deadline = (Get-Date).AddSeconds(240)
    do {
        Start-Sleep -Milliseconds 500
        $panel = Get-CameraPanel
        $launcher.Refresh()
        if ($launcher.HasExited -and -not $panel) { throw '启动失败，请查看 camera-launcher-error.log。' }
    } while (-not $panel -and (Get-Date) -lt $deadline)
    if (-not $panel) { throw '启动超时，请查看 camera-launcher.log。' }
}
Write-Host ('原厂界面（取景与拍照尚未实现）：' + $panel.url)
Start-Process -FilePath $panel.url
