# Background launcher for the local service:
#   - backend  FastAPI (uvicorn) -> http://localhost:8000
#   - frontend Vite (npm run dev) -> http://localhost:5213
# Each process runs hidden (no console window); stdout/stderr are redirected
# into logs\ so you can inspect startup/errors there.
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$logDir = Join-Path $root "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Write-Log([string]$msg) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
    Add-Content -Path (Join-Path $logDir "startup.log") -Value $line -Encoding UTF8
}

function Test-Port([int]$port) {
    return [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
}

# ---- Backend: FastAPI on port 8000 ----
if (Test-Port 8000) {
    Write-Log "backend already running (port 8000), skip"
} else {
    $py = Join-Path $root "api\.venv\Scripts\python.exe"
    if (-not (Test-Path $py)) {
        Write-Log "ERROR: virtualenv not found at $py - run 'python -m venv .venv' in api/ first"
        exit 1
    }
    $p = Start-Process -FilePath $py `
        -ArgumentList "-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8000" `
        -WorkingDirectory (Join-Path $root "api") `
        -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logDir "backend.log") `
        -RedirectStandardError  (Join-Path $logDir "backend.err.log") `
        -PassThru
    Write-Log "backend started PID=$($p.Id) on port 8000"
}

# ---- Frontend: Vite on port 5213 ----
if (Test-Port 5213) {
    Write-Log "frontend already running (port 5213), skip"
} else {
    $fe = Join-Path $root "frontend"
    if (-not (Test-Path (Join-Path $fe "node_modules"))) {
        Write-Log "ERROR: frontend\node_modules not found - run 'npm install' in frontend/ first"
        exit 1
    }
    $p = Start-Process -FilePath "cmd.exe" `
        -ArgumentList "/c","npm run dev" `
        -WorkingDirectory $fe `
        -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logDir "frontend.log") `
        -RedirectStandardError  (Join-Path $logDir "frontend.err.log") `
        -PassThru
    Write-Log "frontend started PID=$($p.Id) on port 5213"
}

Write-Log "done. backend http://localhost:8000 | frontend http://localhost:5213"
