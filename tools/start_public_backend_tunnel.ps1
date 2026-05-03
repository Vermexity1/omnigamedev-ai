param(
    [string]$BackendUrl = "http://127.0.0.1:8787"
)

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Cloudflared = Join-Path $Root "tools\cloudflared.exe"
$Logs = Join-Path $Root ".logs"
$StdOut = Join-Path $Logs "cloudflared.out.log"
$StdErr = Join-Path $Logs "cloudflared.err.log"

if (-not (Test-Path $Cloudflared)) {
    New-Item -ItemType Directory -Force -Path (Join-Path $Root "tools") | Out-Null
    Invoke-WebRequest -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" -OutFile $Cloudflared
}

New-Item -ItemType Directory -Force -Path $Logs | Out-Null
Remove-Item $StdOut, $StdErr -ErrorAction SilentlyContinue

$Process = Start-Process -FilePath $Cloudflared `
    -ArgumentList @("tunnel", "--url", $BackendUrl, "--no-autoupdate") `
    -RedirectStandardOutput $StdOut `
    -RedirectStandardError $StdErr `
    -WindowStyle Hidden `
    -PassThru

Start-Sleep -Seconds 8
$LogText = (Get-Content $StdErr -ErrorAction SilentlyContinue) -join "`n"
$Match = [regex]::Match($LogText, "https://[a-zA-Z0-9-]+\.trycloudflare\.com")

[pscustomobject]@{
    ProcessId = $Process.Id
    Url = if ($Match.Success) { $Match.Value } else { "" }
    Log = $StdErr
}
