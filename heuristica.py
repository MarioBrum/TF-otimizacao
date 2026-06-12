import random
import time


def decodificacao_delta(permutacao, p, s_prefixo, i):
    """
    Decodificação parcial (delta evaluation).

    Reaproveita os tempos de início já calculados para as posições
    1..i-1 (que não mudaram) e re-decodifica apenas das posições
    i..n em diante.

    Parâmetros
    ----------
    permutacao : list[int]
        Permutação completa (já com o movimento aplicado).
    p : list[float]
        Tempos de processamento por índice de tarefa.
    s_prefixo : dict[int, float]
        Tempos de início já conhecidos das tarefas nas posições
        0..i-1 da permutação (calculados em uma decodificação anterior
        e que permanecem válidos, pois essas posições não mudaram).
    i : int
        Índice (0-based) a partir do qual a permutação foi alterada
        e precisa ser re-decodificada.

    Retorna
    -------
    s : dict[int, float]
        Tempos de início completos (prefixo reaproveitado + novos).
    makespan : float
        max(s_i + p_i) sobre todas as tarefas.
    """
    # Copia o prefixo reaproveitado — essas tarefas continuam "agendadas"
    # e participam do cálculo de candidatos/validação para as posições i..n
    s = dict(s_prefixo)

    # Re-decodifica apenas a partir da posição i
    for tarefa_k in permutacao[i:]:
        p_k = p[tarefa_k]

        # Candidatos: t = 0 e extremos superiores dos intervalos de bloqueio,
        # considerando TODAS as tarefas já agendadas (prefixo + novas)
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
    """Decodificação completa (caso particular: i = 0, sem prefixo)."""
    return decodificacao_delta(permutacao, p, s_prefixo={}, i=0)


def construir_prefixo(permutacao, s, i):
    """
    Extrai o dicionário de prefixo (tarefas nas posições 0..i-1)
    a partir de um resultado de decodificação anterior.
    """
    return {tarefa: s[tarefa] for tarefa in permutacao[:i]}

def solucao_inicial(p):
    """
    Gera a solução inicial ordenando os índices das tarefas
    em ordem decrescente de p[i], usando sorted() com reverse=True.
    """
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
    """
    VND com insertion-shift e 2-exchange, First Improvement.
    Recebe (opcionalmente) o s já calculado para 'perm', evitando
    uma decodificação completa redundante no início.

    Retorna (melhor_perm, s_melhor, melhor_makespan).
    """
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

        # --- Fase 1: insertion-shift até ótimo local ---
        melhorou_shift = True
        while melhorou_shift:
            melhorou_shift = False
            for i in range(n):
                for j in range(n):
                    if i == j:
                        continue

                    corte = min(i, j)
                    vizinho = insertion_shift(melhor_perm, i, j)

                    # reaproveita s[0..corte-1] da solução atual
                    s_prefixo = construir_prefixo(melhor_perm, s_melhor, corte)
                    s_viz, mk = decodificacao_delta(vizinho, p, s_prefixo, corte)

                    if mk < melhor_makespan:
                        melhor_perm, s_melhor, melhor_makespan = vizinho, s_viz, mk
                        melhorou_shift = True
                        algo_melhorou = True
                        break  # first improvement
                if melhorou_shift:
                    break

        # --- Fase 2: 2-exchange até ótimo local ---
        melhorou_exchange = True
        while melhorou_exchange:
            melhorou_exchange = False
            for i in range(n):
                for j in range(i + 1, n):
                    corte = i  # = min(i, j), pois i < j
                    vizinho = two_exchange(melhor_perm, i, j)

                    s_prefixo = construir_prefixo(melhor_perm, s_melhor, corte)
                    s_viz, mk = decodificacao_delta(vizinho, p, s_prefixo, corte)

                    if mk < melhor_makespan:
                        melhor_perm, s_melhor, melhor_makespan = vizinho, s_viz, mk
                        melhorou_exchange = True
                        algo_melhorou = True
                        break  # first improvement
                if melhorou_exchange:
                    break

        # se algo melhorou (em qualquer fase), volta ao insertion-shift

    return melhor_perm, s_melhor, melhor_makespan


def perturbacao(perm, k):
    """
    Aplica k trocas 2-exchange aleatórias e retorna a permutação
    perturbada junto com o índice de corte (menor posição tocada),
    para permitir delta evaluation na re-decodificação seguinte.
    """
    nova = perm.copy()
    n = len(nova)
    corte = n  # caso k == 0, nada muda

    for _ in range(k):
        i, j = random.sample(range(n), 2)
        nova[i], nova[j] = nova[j], nova[i]
        corte = min(corte, i, j)

    return nova, corte


def ils(p, k=5, tempo_max=60, estagnacao_max=500, fator_reset=0.2):
    n = len(p)
    iter_reset = max(1, int(fator_reset * estagnacao_max))

    # --- Solução inicial (item 3) + busca local ---
    perm_atual = solucao_inicial(p)
    perm_atual, s_atual, makespan_atual = busca_local_vnd(perm_atual, p)

    melhor_perm = perm_atual.copy()
    melhor_s = s_atual
    melhor_makespan = makespan_atual

    iter_sem_melhora = 0
    inicio = time.time()

    while iter_sem_melhora < estagnacao_max and (time.time() - inicio) < tempo_max:

        # --- 6. Perturbação (com índice de corte) ---
        perm_perturbada, corte_pert = perturbacao(perm_atual, k)

        # decodifica a solução perturbada via delta, reaproveitando s_atual
        s_prefixo = construir_prefixo(perm_atual, s_atual, corte_pert)
        s_pert, makespan_pert = decodificacao_delta(perm_perturbada, p, s_prefixo, corte_pert)

        # --- 4. Busca local sobre a solução perturbada (já com s inicial) ---
        perm_candidata, s_candidata, makespan_candidato = busca_local_vnd(
            perm_perturbada, p, s_inicial=s_pert
        )

        # --- 7. Critério de aceitação: melhor ou igual ---
        if makespan_candidato <= makespan_atual:
            perm_atual = perm_candidata
            s_atual = s_candidata
            makespan_atual = makespan_candidato

        # --- Atualiza Melhor Solução Global ---
        if makespan_candidato < melhor_makespan:
            melhor_perm = perm_candidata.copy()
            melhor_s = s_candidata
            melhor_makespan = makespan_candidato
            iter_sem_melhora = 0
        else:
            iter_sem_melhora += 1

        # --- 7. Mecanismo de reset do platô ---
        if iter_sem_melhora > 0 and iter_sem_melhora % iter_reset == 0:
            perm_atual = melhor_perm.copy()
            s_atual = melhor_s
            makespan_atual = melhor_makespan

    return melhor_perm, melhor_makespan


p = [4, 2, 3, 5, 1]

melhor_perm, melhor_makespan = ils(p, k=3, tempo_max=5, estagnacao_max=100)

print("Melhor permutação encontrada:", melhor_perm)
print("Melhor makespan:", melhor_makespan)