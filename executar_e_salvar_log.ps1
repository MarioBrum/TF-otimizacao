# Script para executar admHighs e admGurobi em paralelo
$workDir = "c:\trabalho_otimizacao\TF-otimizacao"
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$logFileHighs = Join-Path $workDir "log_admHighs_$timestamp.txt"
$logFileGurobi = Join-Path $workDir "log_admGurobi_$timestamp.txt"

Set-Location $workDir

# Script para admHighs
$script1 = @"
Set-Location "$workDir"
julia admHighs.jl
"@

# Script para admGurobi
$script2 = @"
Set-Location "$workDir"
julia admGurobi.jl
"@

Write-Host "Iniciando execucoes em paralelo..."
Write-Host ""

# Executar em paralelo
$proc1 = Start-Process powershell -ArgumentList "-NoExit", "-Command", "$script1 | Tee-Object -FilePath '$logFileHighs'" -PassThru
$proc2 = Start-Process powershell -ArgumentList "-NoExit", "-Command", "$script2 | Tee-Object -FilePath '$logFileGurobi'" -PassThru

Write-Host "OK - Ambas as execucoes iniciadas!"
Write-Host ""
Write-Host "Logs serao salvos em:"
Write-Host "  - $logFileHighs"
Write-Host "  - $logFileGurobi"
Write-Host ""
Write-Host "Feche as janelas quando terminarem."
