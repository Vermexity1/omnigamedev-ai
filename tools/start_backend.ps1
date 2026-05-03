param(
    [string]$AccessCode = ""
)

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Logs = Join-Path $Root ".logs"
$StdOut = Join-Path $Logs "backend.out.log"
$StdErr = Join-Path $Logs "backend.err.log"

New-Item -ItemType Directory -Force -Path $Logs | Out-Null
Remove-Item $StdOut, $StdErr -ErrorAction SilentlyContinue

Get-NetTCPConnection -LocalPort 8787 -ErrorAction SilentlyContinue |
    Where-Object { $_.State -eq "Listen" } |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }

if ($AccessCode) {
    $env:OMNIGAMEDEV_API_TOKEN = $AccessCode
}

Start-Process -FilePath $Python `
    -ArgumentList @("-m", "uvicorn", "ide.backend.app:app", "--host", "127.0.0.1", "--port", "8787") `
    -WorkingDirectory $Root `
    -RedirectStandardOutput $StdOut `
    -RedirectStandardError $StdErr `
    -WindowStyle Hidden `
    -PassThru
