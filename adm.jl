using JuMP
using HiGHS

# https://github.com/mrpritt/otimizacao-combinatoria/blob/main/demos/D02-tsp-h2.ipynb

function solver(file)
    #read_file
    str_conteudo = read(file, String)
    tokens = split(str_conteudo)

    if isempty(tokens)
        return
    end

    n = parse(Int, tokens[1])
    p = [parse(Int, tokens[i+1]) for i in 1:n]

    println("Resolvendo via MILP: $file ($n tarefas)")

    model = Model(HiGHS.Optimizer)

    set_attribute(model, "time_limit", 7200.0) #2h
    set_attribute(model, "mip_rel_gap", 0.01) # Para parar quando estiver a 1% do ótimo

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

    @time optimize!(model)

    println("A solução do modelo básico tem valor" ,objective_value(model))

    # optimize!(model)

    # status = termination_status(model)
    # if status == OPTIMAL || status == TIME_LIMIT
    #     println("Status: ", status)
    #     println("Makespan encontrado: ", objective_value(model))
    #     # Se quiser ver os tempos de início:
    #     # for i in 1:n; println("s[$i] = ", value(s[i])); end
    # else
    #     println("Status da busca: ", status)
    # end

end

solver("adm_50_1.dat")
