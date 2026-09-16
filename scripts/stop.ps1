$ErrorActionPreference = "Stop"

$containerName = "pm-mvp"
$existingContainer = docker container ls --all --quiet --filter "name=^/${containerName}$"

if ($existingContainer) {
    docker container rm --force $containerName | Out-Null
    Write-Host "Project Management MVP stopped."
} else {
    Write-Host "Project Management MVP is not running."
}

