# Stop the local service by killing the processes listening on ports 8000/5213.
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$logDir = Join-Path $root "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir "stop.log"

$stopped = 0
foreach ($port in 8000, 5213) {
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($c in $conns) {
        $procId = $c.OwningProcess
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        Add-Content -Path $logFile -Value ("[{0}] stopped port {1} process PID={2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $port, $procId) -Encoding UTF8
        $stopped++
    }
}

if ($stopped -eq 0) {
    Add-Content -Path $logFile -Value ("[{0}] no running service found" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss")) -Encoding UTF8
}
