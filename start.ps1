$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host ""
Write-Host " Kazia - Assistant Juridique IA"
Write-Host " --------------------------------"
Write-Host " Verification de l'environnement..."
Write-Host ""

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host " [ERREUR] .venv introuvable. Executez d'abord :"
    Write-Host "          python -m venv .venv"
    Write-Host "          .venv\Scripts\pip install -r requirements_rag.txt"
    exit 1
}

if (-not (Test-Path (Join-Path $root "static\index.html"))) {
    Write-Host " [ERREUR] static\index.html introuvable."
    exit 1
}

function Test-HttpReady($port) {
    try {
        $r = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$port/api/status" -TimeoutSec 1
        return $r.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Test-PortFree($port) {
    $listener = $null
    try {
        $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Parse("127.0.0.1"), $port)
        $listener.Start()
        return $true
    } catch {
        return $false
    } finally {
        if ($listener) {
            $listener.Stop()
        }
    }
}

$existingPort = 8000..8010 | Where-Object { Test-HttpReady $_ } | Select-Object -First 1
if ($existingPort) {
    $port = $existingPort
    Write-Host " Serveur deja actif sur le port $port."
} else {
    $port = 8000..8010 | Where-Object { Test-PortFree $_ } | Select-Object -First 1
    if (-not $port) {
        Write-Host " [ERREUR] Aucun port libre trouve entre 8000 et 8010."
        Write-Host " Fermez les anciens serveurs Python/Uvicorn puis relancez start.bat."
        exit 1
    }

    Write-Host " Port choisi : $port"
    Write-Host " Demarrage du serveur API..."

    $args = "-m uvicorn api:app --host 127.0.0.1 --port $port"
    Start-Process -FilePath $python -ArgumentList $args -WorkingDirectory $root -WindowStyle Normal
}

Write-Host " Attente du serveur..."
$ready = $false
for ($i = 1; $i -le 30; $i++) {
    if (Test-HttpReady $port) {
        $ready = $true
        break
    }
    Start-Sleep -Seconds 1
}

if ($ready) {
    $url = "http://127.0.0.1:$port"
    Write-Host " Serveur pret : $url"
    Start-Process $url
} else {
    Write-Host ""
    Write-Host " [ERREUR] Le serveur n'a pas repondu apres 30 secondes."
    Write-Host " Lancez cette commande pour voir l'erreur exacte :"
    Write-Host " `"$python`" -m uvicorn api:app --host 127.0.0.1 --port $port"
    exit 1
}

Write-Host ""
Write-Host " Gardez la fenetre Python/Uvicorn ouverte pendant l'utilisation."
