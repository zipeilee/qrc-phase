```
    Transverse Field Ising Model
```
function TFIM(N::Int64, g::Float64; J=1.0)
    os = OpSum()
    for j=1:N-1
        os += -J, "Z", j, "Z", j+1
    end

    for j=1:N
        os += -g, "X", j
    end

    os += 0.01, "Z", 1  # 添加惩罚项

    sites = siteinds("Qubit", N)
    H = MPO(os, sites)
    return H, sites
end



```
    Cold Atoms Hamiltonian
```
function cold_atoms(N::Int64, Ω, Δ, Rb; a=1.0)
    os = OpSum()

    # 第一部分：sum_i (Ω / 2) X_i
    for i in 1:N
        os += (Ω / 2), "X", i
    end

    # 第二部分：sum_i Δ N_i
    # N_i = (1 - Z_i) / 2
    for i in 1:N
        os += -Δ / 2, "Id", i  # -Δ * (1/2)
        os += Δ / 2, "Z", i    # -Δ * (-Z_i / 2)
    end

    # 第三部分：sum_i<j (Rb / (a * |i - j|)^6) N_i N_j
    for i in 1:N-1
        for j in i+1:N
            distance = abs(i - j)
            coeff = (Rb / (a * distance))^6 / 4  # 因为 N_i = (1 - Z_i) / 2
            os += coeff, "Id", i, "Id", j
            os += -coeff, "Id", i, "Z", j
            os += -coeff, "Z", i, "Id", j
            os += coeff, "Z", i, "Z", j
        end
    end

    sites = siteinds("Qubit", N)
    H = MPO(os, sites)
    return H, sites
end



```
    Cluster State Hamiltonian
```
function ClusterHamiltonian(N::Int, periodic::Bool=true)
    os = OpSum()

    for j=1:N
        left = (j == 1 && !periodic) ? nothing : (j==1 ? N : j-1)
        right = (j == N && !periodic) ? nothing : (j==N ? 1 : j+1)

        if left != nothing && right != nothing
            os += -1.0, "Z", left, "X", j, "Z", right
        end
    end

    sites = siteinds("Qubit", N)
    H = MPO(os, sites)
    return H, sites
end



```
    ToricCode Hamiltonian
```
function ToricCode(H::Int, W::Int)
    os = OpSum()
    N = H * W

    idx = (x, y) -> (y-1) * W + x

    for x=1:W÷2, y=1:H
        x0 = 2*(x-1) + ((y % 2 == 1) ? 1 : 2)

        p1 = idx(x0, y)
        p2 = idx(x0%W+1, y)
        p3 = idx(x0%W+1, y%H+1)
        p4 = idx(x0, y%H+1)

        os += -1.0, "Z", p1, "Z", p2, "Z", p3, "Z", p4
    end

    for x=1:W÷2, y=1:H
        x0 =  2*(x-1) + (y % 2) + 1

        s1 = idx(x0%W+1, y%H+1)
        s2 = idx(x0, y%H+1)
        s3 = idx(x0%H+1, y)
        s4 = idx(x0, y)

        os += -1.0, "X", s1, "X", s2, "X", s3, "X", s4
    end

    sites = siteinds("Qubit", N)
    ham = MPO(os, sites)
    return ham, sites
end



```
    Extend SSH Model Hamiltonian
```
function eSSH(sites; J1::Float64=1.0, J2::Float64=0.5, delta::Float64=0.0, periodic::Bool=false)
    nbit = length(sites)
    os = OpSum()
    
    # 遍历每一对相邻的量子位
    for i in 1:(periodic ? nbit : nbit-1)
        j = i + 1
        j = j > nbit ? 1 : j  # 周期性边界条件
        J = isodd(i) ? J1 : J2

        # 添加 Hamiltonian 交互项
        os += J, "X", i, "X", j
        os += J, "Y", i, "Y", j
        os += J * delta, "Z", i, "Z", j
    end

    os += 0.01, "Z", 1  # 添加惩罚项
    H = MPO(os, sites)
    return H, sites
end


function clusterIsing(N, h1, h2)
    os = OpSum()

    for i in 1:N-2
        os += -1.0, "Z", i, "X", i+1, "Z", i+2
    end

    for i in 1:N
        os += -h1, "X", i
    end

    for i in 1:N-1
        os += -h2, "X", i, "X", i+1
    end


    os += 0.01, "X", 1  # 添加惩罚项 
    sites = siteinds("Qubit", N)
    H = MPO(os, sites)

    return H, sites
end

```
    Cluster Ising 2
```
function cluster_ising_2(sites, λ::Number)
    # 创建自旋-1/2站点索引
    nbit = length(sites)

    # 用 AutoMPO 构造哈密顿量
    ampo = AutoMPO()

    # cluster term: -X_{i-1} Z_i X_{i+1}
    for i in 1:nbit
        left = (i == 1 ? nbit : i - 1)
        right = (i == nbit ? 1 : i + 1)
        add!(ampo, -1.0, "X", left, "Z", i, "X", right)
    end

    # lambda term: Y_i Y_{i+1}
    for i in 1:nbit
        j = (i % nbit) + 1
        add!(ampo, λ, "Y", i, "Y", j)
    end

    add!(ampo, 0.01, "Y", 1)  # 添加惩罚项
    # 构造 MPO 哈密顿量
    H = MPO(ampo, sites)

    return H, sites
end
