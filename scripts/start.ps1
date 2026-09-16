$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$imageName = "pm-mvp:local"
$containerName = "pm-mvp"

docker build --tag $imageName $projectRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$existingContainer = docker container ls --all --quiet --filter "name=^/${containerName}$"
if ($existingContainer) {
    docker container rm --force $containerName | Out-Null
}

$dockerArguments = @(
    "run", "--detach",
    "--name", $containerName,
    "--publish", "8000:8000"
)

$envFile = Join-Path $projectRoot ".env"
if (Test-Path -LiteralPath $envFile) {
    $dockerArguments += @("--env-file", $envFile)
}

$dockerArguments += $imageName
docker @dockerArguments
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$ready = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    docker exec $containerName python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')" *> $null
    $probeExitCode = $LASTEXITCODE
    $ErrorActionPreference = $previousErrorActionPreference
    if ($probeExitCode -eq 0) {
        $ready = $true
        break
    }
    Start-Sleep -Seconds 1
}

if (-not $ready) {
    Write-Error "Container started, but the API did not become ready within 30 seconds."
    exit 1
}

Write-Host "Project Management MVP is running at http://localhost:8000"
