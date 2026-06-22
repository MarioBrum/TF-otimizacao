#!/usr/bin/env bash
#
# Roda heuristica.py em paralelo para 12 instâncias, gerando um log
# individual por instância em logs/<instancia>.log
#
# Uso:
#   ./rodar_instancias.sh
#
# Pressupõe que:
#   - heuristica.py está no mesmo diretório deste script (ou ajuste HEURISTICA abaixo)
#   - as instâncias .dat estão no diretório DATA_DIR (ajuste abaixo)
#   - python3 está disponível no PATH
#
# Cada instância roda como um processo Python independente, em background.
# O script aguarda todos terminarem antes de encerrar.

set -u

# ---------------------- CONFIGURAÇÃO ----------------------
HEURISTICA="./heuristica.py"      # caminho para o heuristica.py
DATA_DIR="."                       # diretório onde estão os .dat
LOG_DIR="./logs"                   # diretório de saída dos logs
K=3                                 # parâmetro k do ILS (nº de trocas na perturbação)
TEMPO_MAX=7200                      # tempo máximo por instância, em segundos (2h)
ESTAGNACAO_MAX=100                  # iterações sem melhora até parar

INSTANCIAS=(
    "adm_50_1.dat"
    "adm_50_2.dat"
    "adm_50_3.dat"
    "adm_50_4.dat"
    "adm_100_1.dat"
    "adm_100_2.dat"
    "adm_100_3.dat"
    "adm_100_4.dat"
    "adm_1000_1.dat"
    "adm_1000_2.dat"
    "adm_1000_3.dat"
    "adm_1000_4.dat"
)
# ------------------------------------------------------------

mkdir -p "$LOG_DIR"

if [ ! -f "$HEURISTICA" ]; then
    echo "ERRO: não encontrei $HEURISTICA. Ajuste a variável HEURISTICA no início do script." >&2
    exit 1
fi

NCORES=$(nproc 2>/dev/null || echo "desconhecido")
echo "Núcleos de CPU disponíveis: $NCORES"
echo "Disparando ${#INSTANCIAS[@]} instâncias em paralelo (tempo_max=${TEMPO_MAX}s cada)..."
echo "Logs em: $LOG_DIR/"
echo

PIDS=()
NOMES=()

for inst in "${INSTANCIAS[@]}"; do
    caminho_dat="$DATA_DIR/$inst"
    if [ ! -f "$caminho_dat" ]; then
        echo "AVISO: $caminho_dat não encontrado, pulando esta instância." >&2
        continue
    fi

    nome_base="${inst%.dat}"
    log_file="$LOG_DIR/${nome_base}.log"

    # Roda em background, capturando stdout+stderr no log individual.
    # /usr/bin/time -v (se disponível) seria útil para medir pico de memória,
    # mas evitamos a dependência aqui para portabilidade; o próprio
    # heuristica.py já reporta o tempo de execução.
    (
        echo "=== Início: $(date '+%Y-%m-%d %H:%M:%S') ==="
        echo "Instância: $caminho_dat"
        echo "Parâmetros: k=$K tempo_max=$TEMPO_MAX estagnacao_max=$ESTAGNACAO_MAX"
        echo
        python3 "$HEURISTICA" "$caminho_dat" "$K" "$TEMPO_MAX" "$ESTAGNACAO_MAX"
        status=$?
        echo
        echo "=== Fim: $(date '+%Y-%m-%d %H:%M:%S') (exit code: $status) ==="
    ) > "$log_file" 2>&1 &

    pid=$!
    PIDS+=("$pid")
    NOMES+=("$inst")
    echo "  [PID $pid] $inst -> $log_file"
done

echo
echo "Aguardando ${#PIDS[@]} processos terminarem (pode levar até ${TEMPO_MAX}s = $((TEMPO_MAX/3600))h)..."
echo

FALHAS=0
for idx in "${!PIDS[@]}"; do
    pid="${PIDS[$idx]}"
    nome="${NOMES[$idx]}"
    if wait "$pid"; then
        echo "[OK]    $nome (PID $pid) concluído."
    else
        echo "[ERRO]  $nome (PID $pid) terminou com erro. Veja $LOG_DIR/${nome%.dat}.log"
        FALHAS=$((FALHAS+1))
    fi
done

echo
echo "Todas as execuções terminaram. Falhas: $FALHAS / ${#PIDS[@]}"
echo "Resumo rápido dos resultados:"
echo

for inst in "${INSTANCIAS[@]}"; do
    nome_base="${inst%.dat}"
    log_file="$LOG_DIR/${nome_base}.log"
    if [ -f "$log_file" ]; then
        echo "--- $inst ---"
        grep -E "Makespan inicial|Melhor makespan|Tempo de execução|Critério de parada|AVISO" "$log_file" || echo "  (sem saída reconhecida, ver log completo)"
        echo
    fi
done