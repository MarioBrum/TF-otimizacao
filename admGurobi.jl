using JuMP
using Gurobi

# https://github.com/mrpritt/otimizacao-combinatoria/blob/main/demos/D02-tsp-h2.ipynb

function solver(file; WLSACCESSID="67bbaaee-53c8-486f-9f57-deae743d43f5", WLSSECRET="9643dacb-9998-40c7-b862-a8c712ff3174")
    # Configuração de licença WLS do Gurobi
    ENV["GUROBI_WLSACCESSID"] = WLSACCESSID
    ENV["GUROBI_WLSSECRET"] = WLSSECRET
    
    #read_file
    str_conteudo = read(file, String)
    tokens = split(str_conteudo)

    if isempty(tokens)
        return
    end

    n = parse(Int, tokens[1])
    p = [parse(Int, tokens[i+1]) for i in 1:n]

    println("Resolvendo via MILP: $file ($n tarefas)")

    model = Model(Gurobi.Optimizer)

    set_attribute(model, "TimeLimit", 7200.0) #2h
    set_attribute(model, "MIPGap", 0.0) # Para encontrar a solução ótima exata

    @variable(model, x[1:n, 1:n], Bin) # x_ij constraint (4)
    @variable(model, s[1:n] >= 0)      # Tempos de início e constraint (5)
    @variable(model, C_max >= 0)       # Makespan e constraint (6)

    # Big-M: Um limite superior para o tempo total. Geralmente a soma do conjunto é um valor máximo.
    M = sum(p)

    @objective(model, Min, C_max)

    #Restrições
    for i in 1:n
        @constraint(model, C_max >= s[i] + p[i]) #Constraint(1)

        for j in (i+1):n
            d_min = min(p[i], p[j])

            # Se x[i,j] = 1 => i precede j:  s[j] - s[i] >= d_min
            # Se x[i,j] = 0 => j precede i:  s[i] - s[j] >= d_min
            @constraint(model, s[j] - s[i] >= d_min - M * (1 - x[i, j])) #Constraint (2)
            @constraint(model, s[i] - s[j] >= d_min - M * x[i, j]) #Constraint (3) 
        end
    end

    start_time = time()
    @time optimize!(model)
    end_time = time()

    total_time = end_time - start_time

    status = termination_status(model)
    if status == OPTIMAL || status == TIME_LIMIT
        println("Status: ", status)
        println("Makespan encontrado: ", objective_value(model))
        for i in 1:n; println("s[$i] = ", value(s[i])); end
    else
       println("Status da busca: ", status)
    end
    println("Tempo total de execução: ", total_time, " segundos")

end

# Exemplo de uso com WLS:
solver("adm_50_1.dat", WLSACCESSID="YOUR_WLSACCESSID_HERE", WLSSECRET="YOUR_WLSSECRET_HERE")
