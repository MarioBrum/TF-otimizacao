import random
import time
import sys


def decodificacao_delta(permutacao, p, s_prefixo, i, inicio=None, tempo_max=None):
    s = dict(s_prefixo)

    def tempo_esgotado():
        return inicio is not None and tempo_max is not None and (time.time() - inicio) >= tempo_max

    for tarefa_k in permutacao[i:]:
        if tempo_esgotado():
            break

        p_k = p[tarefa_k]

        candidatos = {0.0}
        for tarefa_j, s_j in s.items():
            p_j = p[tarefa_j]
            candidatos.add(s_j + min(p_k, p_j))

        for t in sorted(candidatos):
            valido = True
            for tarefa_j, s_j in s.items():
                p_j = p[tarefa_j]
                if abs(t - s_j) < min(p_k, p_j):
                    valido = False
                    break
            if valido:
                s[tarefa_k] = t
                break

    if not s:
        return s, float('inf')
    makespan = max(s[tarefa] + p[tarefa] for tarefa in s)
    return s, makespan


def _decodificacao_delta_segura(permutacao, p, s_prefixo, i, inicio=None, tempo_max=None):
    """Wrapper que retorna inf se a decodificacao foi interrompida por tempo."""
    s, mk = decodificacao_delta(permutacao, p, s_prefixo, i, inicio, tempo_max)
    total_esperado = len(s_prefixo) + len(permutacao[i:])
    if len(s) < total_esperado:
        return s, float('inf')
    return s, mk


def decodificacao_gulosa(permutacao, p):
    # Sem limite de tempo: deve sempre completar para gerar solução inicial válida
    return decodificacao_delta(permutacao, p, s_prefixo={}, i=0, inicio=None, tempo_max=None)


def construir_prefixo(permutacao, s, i):
    return {tarefa: s[tarefa] for tarefa in permutacao[:i] if tarefa in s}

def solucao_inicial(p):
    return sorted(range(len(p)), key=lambda i: p[i], reverse=True)


def insertion_shift(perm, i, j):
    nova = perm.copy()
    tarefa = nova.pop(i)
    nova.insert(j, tarefa)
    return nova


def two_exchange(perm, i, j):
    nova = perm.copy()
    nova[i], nova[j] = nova[j], nova[i]
    return nova


def busca_local_vnd(perm, p, s_inicial=None, inicio=None, tempo_max=None):
    n = len(perm)
    melhor_perm = perm.copy()

    def tempo_esgotado():
        return inicio is not None and tempo_max is not None and (time.time() - inicio) >= tempo_max

    if s_inicial is None:
        s_melhor, melhor_makespan = decodificacao_gulosa(melhor_perm, p)
    else:
        s_melhor = s_inicial
        # CORREÇÃO: s_inicial pode vir incompleto (decodificação interrompida
        # por tempo esgotado em uma etapa anterior, ex: decodificação da
        # perturbação no ILS). Calcular o makespan apenas sobre as tarefas
        # presentes nesse caso produziria um valor menor que o makespan real
        # da instância completa (solução fisicamente inválida sendo tratada
        # como válida). Tratamos esse caso como inf, igual a uma decodificação
        # que não terminou.
        if len(s_melhor) < n:
            melhor_makespan = float('inf')
        else:
            melhor_makespan = max(s_melhor[t] + p[t] for t in s_melhor)

    algo_melhorou = True
    while algo_melhorou and not tempo_esgotado():
        algo_melhorou = False

        melhorou_shift = True
        while melhorou_shift and not tempo_esgotado():
            melhorou_shift = False
            for i in range(n):
                for j in range(n):
                    if i == j:
                        continue

                    corte = min(i, j)
                    vizinho = insertion_shift(melhor_perm, i, j)

                    s_prefixo = construir_prefixo(melhor_perm, s_melhor, corte)
                    s_viz, mk = _decodificacao_delta_segura(vizinho, p, s_prefixo, corte, inicio=inicio, tempo_max=tempo_max)

                    if mk < melhor_makespan:
                        melhor_perm, s_melhor, melhor_makespan = vizinho, s_viz, mk
                        melhorou_shift = True
                        algo_melhorou = True
                        break
                if melhorou_shift or tempo_esgotado():
                    break

        melhorou_exchange = True
        while melhorou_exchange and not tempo_esgotado():
            melhorou_exchange = False
            for i in range(n):
                for j in range(i + 1, n):
                    corte = i
                    vizinho = two_exchange(melhor_perm, i, j)

                    s_prefixo = construir_prefixo(melhor_perm, s_melhor, corte)
                    s_viz, mk = _decodificacao_delta_segura(vizinho, p, s_prefixo, corte, inicio=inicio, tempo_max=tempo_max)

                    if mk < melhor_makespan:
                        melhor_perm, s_melhor, melhor_makespan = vizinho, s_viz, mk
                        melhorou_exchange = True
                        algo_melhorou = True
                        break
                if melhorou_exchange or tempo_esgotado():
                    break

    return melhor_perm, s_melhor, melhor_makespan


def perturbacao(perm, k):
    nova = perm.copy()
    n = len(nova)
    corte = n

    for _ in range(k):
        i, j = random.sample(range(n), 2)
        nova[i], nova[j] = nova[j], nova[i]
        corte = min(corte, i, j)

    return nova, corte


def ils(p, k=5, tempo_max=60, estagnacao_max=500, fator_reset=0.2):
    n = len(p)
    iter_reset = max(1, int(fator_reset * estagnacao_max))
    inicio = time.time()

    # --- Solução inicial ---
    perm_inicial = solucao_inicial(p)
    s_inicial_dec, makespan_inicial = decodificacao_gulosa(perm_inicial, p)

    # --- Busca local sobre a solução inicial ---
    perm_atual, s_atual, makespan_atual = busca_local_vnd(perm_inicial, p, s_inicial=s_inicial_dec, inicio=inicio, tempo_max=tempo_max)

    melhor_perm = perm_atual.copy()
    melhor_s = s_atual
    melhor_makespan = makespan_atual

    iter_sem_melhora = 0

    while iter_sem_melhora < estagnacao_max and (time.time() - inicio) < tempo_max:
        perm_perturbada, corte_pert = perturbacao(perm_atual, k)

        s_prefixo = construir_prefixo(perm_atual, s_atual, corte_pert)
        s_pert, makespan_pert = _decodificacao_delta_segura(perm_perturbada, p, s_prefixo, corte_pert, inicio=inicio, tempo_max=tempo_max)

        perm_candidata, s_candidata, makespan_candidato = busca_local_vnd(
            perm_perturbada, p, s_inicial=s_pert, inicio=inicio, tempo_max=tempo_max
        )

        if makespan_candidato <= makespan_atual:
            perm_atual = perm_candidata
            s_atual = s_candidata
            makespan_atual = makespan_candidato

        if makespan_candidato < melhor_makespan:
            melhor_perm = perm_candidata.copy()
            melhor_s = s_candidata
            melhor_makespan = makespan_candidato
            iter_sem_melhora = 0
        else:
            iter_sem_melhora += 1

        if iter_sem_melhora > 0 and iter_sem_melhora % iter_reset == 0:
            perm_atual = melhor_perm.copy()
            s_atual = melhor_s
            makespan_atual = melhor_makespan

    tempo_execucao = time.time() - inicio
    parou_por_tempo = tempo_execucao >= tempo_max
    return makespan_inicial, melhor_makespan, tempo_execucao, parou_por_tempo


def readFile(nome_arquivo):
    with open(nome_arquivo, "r") as f:
        linhas = [linha.strip() for linha in f if linha.strip()]

    n = int(linhas[0])
    p = [float(linhas[i]) for i in range(1, n + 1)]

    return p

# CORREÇÃO: nome de arquivo e parâmetros agora podem ser passados via linha de
# comando, permitindo rodar a mesma heuristica.py para várias instâncias sem
# editar o código (necessário para execução em lote/paralela). Sem argumentos,
# mantém o comportamento original (adm_50_1.dat, k=3, tempo_max=7200,
# estagnacao_max=100).
if __name__ == "__main__":
    data_file = sys.argv[1] if len(sys.argv) > 1 else "adm_50_1.dat"
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    tempo_max = float(sys.argv[3]) if len(sys.argv) > 3 else 7200
    estagnacao_max = int(sys.argv[4]) if len(sys.argv) > 4 else 100

    p = readFile(data_file)

    print(f"Instância: {data_file} (n={len(p)})")
    print(f"Parâmetros: k={k}, tempo_max={tempo_max}s, estagnacao_max={estagnacao_max}")

    makespan_inicial, melhor_makespan, tempo_execucao, parou_por_tempo = ils(
        p, k=k, tempo_max=tempo_max, estagnacao_max=estagnacao_max
    )

    print(f"Makespan inicial:  {makespan_inicial:.2f}")
    print(f"Melhor makespan:   {melhor_makespan:.2f}")
    print(f"Tempo de execução: {tempo_execucao:.4f}s")

    if melhor_makespan == float('inf'):
        print("AVISO: nenhuma solução completa e viável foi encontrada dentro do tempo limite.")

    if parou_por_tempo:
        print("Critério de parada: limite de tempo atingido.")
    else:
        print("Critério de parada: estagnação (sem melhora por iterações consecutivas).")