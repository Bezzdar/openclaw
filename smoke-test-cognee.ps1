param(
    [string]$CogneeUrl = "http://localhost:8001",
    [string]$DatasetName = "e2e_memory_test",
    [string]$InputFile = ".\e2e-memory.txt",
    [string]$Query = "Кто руководит проектом Phoenix и где он работает?"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $InputFile)) {
@'
Иван Петров руководит проектом Phoenix.
Иван Петров работает в отделе аналитики компании.
Проект Phoenix связан с системой мониторинга и отчётности.
'@ | Set-Content -Encoding utf8 $InputFile
}

Write-Host "1) Health check: $CogneeUrl/health"
$health = Invoke-RestMethod -Uri "$CogneeUrl/health" -Method Get
$health | ConvertTo-Json -Depth 5

Write-Host "2) Add document to dataset '$DatasetName'"
$absPath = (Resolve-Path $InputFile).Path
curl.exe -sS -X POST "$CogneeUrl/api/v1/add" `
  -F "datasetName=$DatasetName" `
  -F "data=@$absPath"

Write-Host ""
Write-Host "3) Run cognify"
$cognifyBody = @{
    datasets = @($DatasetName)
    run_in_background = $false
} | ConvertTo-Json -Depth 5

$cognifyResult = Invoke-RestMethod `
    -Uri "$CogneeUrl/api/v1/cognify" `
    -Method Post `
    -ContentType "application/json" `
    -Body $cognifyBody

$cognifyResult | ConvertTo-Json -Depth 8

Write-Host "4) Search in knowledge graph"
$searchPath = Join-Path $PSScriptRoot "search-request.json"
@{
    datasets = @($DatasetName)
    search_type = "GRAPH_COMPLETION"
    query = $Query
    top_k = 5
} | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 $searchPath

curl.exe -sS -X POST "$CogneeUrl/api/v1/search" `
  -H "Content-Type: application/json" `
  --data-binary "@$searchPath"

Write-Host ""
Write-Host "Done. If search contains facts from the file, Cognee graph memory works."
