import random
import time


def decodificacao_delta(permutacao, p, s_prefixo, i):
    s = dict(s_prefixo)

    for tarefa_k in permutacao[i:]:
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

    makespan = max(s[tarefa] + p[tarefa] for tarefa in s)
    return s, makespan


def decodificacao_gulosa(permutacao, p):
    return decodificacao_delta(permutacao, p, s_prefixo={}, i=0)


def construir_prefixo(permutacao, s, i):
    return {tarefa: s[tarefa] for tarefa in permutacao[:i]}

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


def busca_local_vnd(perm, p, s_inicial=None):
    n = len(perm)
    melhor_perm = perm.copy()

    if s_inicial is None:
        s_melhor, melhor_makespan = decodificacao_gulosa(melhor_perm, p)
    else:
        s_melhor = s_inicial
        melhor_makespan = max(s_melhor[t] + p[t] for t in s_melhor)

    algo_melhorou = True
    while algo_melhorou:
        algo_melhorou = False

        melhorou_shift = True
        while melhorou_shift:
            melhorou_shift = False
            for i in range(n):
                for j in range(n):
                    if i == j:
                        continue

                    corte = min(i, j)
                    vizinho = insertion_shift(melhor_perm, i, j)

                    s_prefixo = construir_prefixo(melhor_perm, s_melhor, corte)
                    s_viz, mk = decodificacao_delta(vizinho, p, s_prefixo, corte)

                    if mk < melhor_makespan:
                        melhor_perm, s_melhor, melhor_makespan = vizinho, s_viz, mk
                        melhorou_shift = True
                        algo_melhorou = True
                        break
                if melhorou_shift:
                    break

        melhorou_exchange = True
        while melhorou_exchange:
            melhorou_exchange = False
            for i in range(n):
                for j in range(i + 1, n):
                    corte = i
                    vizinho = two_exchange(melhor_perm, i, j)

                    s_prefixo = construir_prefixo(melhor_perm, s_melhor, corte)
                    s_viz, mk = decodificacao_delta(vizinho, p, s_prefixo, corte)

                    if mk < melhor_makespan:
                        melhor_perm, s_melhor, melhor_makespan = vizinho, s_viz, mk
                        melhorou_exchange = True
                        algo_melhorou = True
                        break
                if melhorou_exchange:
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
    perm_atual, s_atual, makespan_atual = busca_local_vnd(perm_inicial, p, s_inicial=s_inicial_dec)

    melhor_perm = perm_atual.copy()
    melhor_s = s_atual
    melhor_makespan = makespan_atual

    iter_sem_melhora = 0

    while iter_sem_melhora < estagnacao_max and (time.time() - inicio) < tempo_max:
        perm_perturbada, corte_pert = perturbacao(perm_atual, k)

        s_prefixo = construir_prefixo(perm_atual, s_atual, corte_pert)
        s_pert, makespan_pert = decodificacao_delta(perm_perturbada, p, s_prefixo, corte_pert)

        perm_candidata, s_candidata, makespan_candidato = busca_local_vnd(
            perm_perturbada, p, s_inicial=s_pert
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
    return makespan_inicial, melhor_makespan, tempo_execucao


def readFile(nome_arquivo):
    with open(nome_arquivo, "r") as f:
        linhas = [linha.strip() for linha in f if linha.strip()]

    n = int(linhas[0])
    p = [float(linhas[i]) for i in range(1, n + 1)]

    return p

# p = [4, 2, 3, 5, 1]
p = readFile("adm_1000_1.dat");

makespan_inicial, melhor_makespan, tempo_execucao = ils(p, k=3, tempo_max=5, estagnacao_max=100)

print(f"Makespan inicial:  {makespan_inicial:.2f}")
print(f"Melhor makespan:   {melhor_makespan:.2f}")
print(f"Tempo de execução: {tempo_execucao:.4f}s")