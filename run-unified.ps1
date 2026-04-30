param(
    [switch]$WithCognee,
    [switch]$WithDebug
)

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example"
}

$profileArgs = @()
if ($WithCognee) {
    $profileArgs += "--profile"
    $profileArgs += "cognee"
}
if ($WithDebug) {
    $profileArgs += "--profile"
    $profileArgs += "debug"
}

docker compose @profileArgs up -d --build
docker compose ps
