# Script para executar admHighs em 3 lotes de 2 instancias paralelas
$workDir = "c:\trabalho_otimizacao\TF-otimizacao"
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'

# Definir 3 lotes de 2 instancias cada
$lotes = @(
    @("adm_50_1.dat", "adm_50_3.dat"),
    @("adm_100_1.dat", "adm_100_3.dat"),
    @("adm_1000_1.dat", "adm_1000_3.dat")
)

Set-Location $workDir

Write-Host "Iniciando execucoes admHighs em 3 lotes de 2 instancias"
Write-Host "Tempo estimado total: ~6 horas"
Write-Host ""

# Funcao para executar uma instancia
function Executar-Instancia($instancia, $logFile) {
    # Criar arquivo Julia temporario
    $tempJuliaFile = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "solver_$([guid]::NewGuid()).jl")
    
    $juliaCode = @"
using JuMP
using HiGHS

function solver(file)
    str_conteudo = read(file, String)
    tokens = split(str_conteudo)
    if isempty(tokens)
        return
    end
    n = parse(Int, tokens[1])
    p = [parse(Int, tokens[i+1]) for i in 1:n]
    println("Resolvendo via MILP: " * file * " (" * string(n) * " tarefas)")
    model = Model(HiGHS.Optimizer)
    set_attribute(model, "time_limit", 7200.0)
    set_attribute(model, "mip_rel_gap", 0.0)
    @variable(model, x[1:n, 1:n], Bin)
    @variable(model, s[1:n] >= 0)
    @variable(model, C_max >= 0)
    M = sum(p)
    @objective(model, Min, C_max)
    for i in 1:n
        @constraint(model, C_max >= s[i] + p[i])
        for j in (i+1):n
            d_min = min(p[i], p[j])
            @constraint(model, s[j] - s[i] >= d_min - M * (1 - x[i, j]))
            @constraint(model, s[i] - s[j] >= d_min - M * x[i, j])
        end
    end
    start_time = time()
    @time optimize!(model)
    end_time = time()
    total_time = end_time - start_time
    status = termination_status(model)
    if status == OPTIMAL || status == TIME_LIMIT
        println("Status: " * string(status))
        println("Makespan encontrado: " * string(objective_value(model)))
        for i in 1:n
            println("s[" * string(i) * "] = " * string(value(s[i])))
        end
    else
        println("Status da busca: " * string(status))
    end
    println("Tempo total de execucao: " * string(total_time) * " segundos")
end

solver("$instancia")
"@
    
    # Salvar codigo Julia em arquivo temporario
    $juliaCode | Out-File -FilePath $tempJuliaFile -Encoding UTF8
    
    $cmdString = @"
Set-Location '$workDir'

'=' * 80 | Out-File -FilePath '$logFile' -Encoding ASCII
'LOG DE EXECUCAO - admHighs.jl' | Out-File -FilePath '$logFile' -Encoding ASCII -Append
'Instancia: $instancia' | Out-File -FilePath '$logFile' -Encoding ASCII -Append
'Data: ' + (Get-Date -Format 'dd/MM/yyyy HH:mm:ss') | Out-File -FilePath '$logFile' -Encoding ASCII -Append
'=' * 80 | Out-File -FilePath '$logFile' -Encoding ASCII -Append
'' | Out-File -FilePath '$logFile' -Encoding ASCII -Append
'[INICIANDO] $instancia - ' + (Get-Date -Format 'HH:mm:ss') | Out-File -FilePath '$logFile' -Encoding ASCII -Append
'' | Out-File -FilePath '$logFile' -Encoding ASCII -Append

Write-Host "Executando: $instancia"
Write-Host ""

julia '$tempJuliaFile' 2>&1 | ForEach-Object {
    Write-Host `$_
    `$_ | Out-File -FilePath '$logFile' -Encoding ASCII -Append
}

Write-Host ""
'' | Out-File -FilePath '$logFile' -Encoding ASCII -Append
'[CONCLUIDO] $instancia - ' + (Get-Date -Format 'HH:mm:ss') | Out-File -FilePath '$logFile' -Encoding ASCII -Append
'=' * 80 | Out-File -FilePath '$logFile' -Encoding ASCII -Append

Write-Host "[CONCLUIDO] $instancia"
Remove-Item '$tempJuliaFile' -Force -ErrorAction SilentlyContinue
"@
    
    return (Start-Process powershell -ArgumentList "-NoExit", "-Command", $cmdString -PassThru)
}

# Executar cada lote
for ($loteNum = 0; $loteNum -lt $lotes.Count; $loteNum++) {
    $lote = $lotes[$loteNum]
    $inicioLote = Get-Date
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "LOTE $($loteNum + 1) de 3" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Instancias: $($lote[0]), $($lote[1])"
    Write-Host "Hora: $(Get-Date -Format 'HH:mm:ss')"
    Write-Host ""
    
    $processos = @()
    
    # Executar as 2 instancias do lote em paralelo
    foreach ($instancia in $lote) {
        $logFile = Join-Path $workDir "log_$($instancia.Replace('.dat', ''))_$timestamp.txt"
        Write-Host "  Iniciando: $instancia"
        $proc = Executar-Instancia $instancia $logFile
        $processos += $proc
    }
    
    Write-Host ""
    Write-Host "  Aguardando conclusao das 2 instancias..."
    Write-Host ""
    
    # Aguardar conclusao de ambas as instancias do lote
    foreach ($proc in $processos) {
        $proc | Wait-Process
    }
    
    $fimLote = Get-Date
    $duracao = $fimLote - $inicioLote
    
    Write-Host "  OK - Lote $($loteNum + 1) concluido!"
    Write-Host "  Duracao: $([int]$duracao.TotalSeconds) segundos"
    Write-Host ""
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "EXECUCAO COMPLETA!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Todos os 6 logs foram salvos na raiz do projeto."