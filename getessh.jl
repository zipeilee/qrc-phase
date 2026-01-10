using ITensors, ITensorMPS
using HDF5
using Printf

include("hamiltonian.jl")


```
    eSSH 固定 δ 扫描J2
```
N = 128 # 系统大小
delta_range = collect(0.0:0.5:4.0) # 将 delta 范围收集成数组
J2_values = collect(0.0:0.001:3.0) # 将 J2 范围收集成一个数组

# --- 设置整个扫描的初始 MPS ---
# 从一个 Neel 态开始
sites = siteinds("S=1/2", N) # 需要 sites 来创建 Neel 态
state = [isodd(j) ? "0" : "1" for j in 1:N]
last_psi = MPS(sites, state)
println("Starting zigzag scan with initial Neel state.")
# ------------------------------

# 开始之字形扫描
# enumerate(delta_range) 会返回 (索引, 值) 对
for (delta_idx, δ) in enumerate(delta_range)
    formatted_δ = @sprintf("%.1f", δ)
    println("\nScanning for delta = $formatted_δ (Step $(delta_idx)/$(length(delta_range)))")

    # 根据 δ 的索引 (delta_idx) 决定 J2 的扫描方向
    is_J2_ascending = isodd(delta_idx)
    current_J2_scan = is_J2_ascending ? J2_values : reverse(J2_values)

    # 在 J2 循环内部，总是使用上一个计算出的 MPS
    for J2 in current_J2_scan
        global last_psi # Declare last_psi as global within this scope

        formatted_J2 = @sprintf("%.4f", J2)
        println("    J2 = $formatted_J2")

        # 构建 Hamiltonian (需要 sites，从 last_psi 获取以确保一致性)
        # Make sites local to this inner loop iteration
        local sites = siteinds(last_psi)

        H, sites = eSSH(sites, J1=1.0, J2=J2, delta=δ, periodic=false)

        # DMRG 参数
        nsweeps = 10
        maxdim = [16, 32, 100, 100, 200]
        cutoff = 1E-10

        # 运行 DMRG 计算基态，使用 last_psi 作为初始猜测
        energy, psi = dmrg(H, last_psi, nsweeps=nsweeps, maxdim=maxdim, cutoff=cutoff)

        println("    Energy = $energy")

        # 保存基态 MPS 到 HDF5 文件
        output_dir = "MPS/eSSH/N$(N)_p_p/$(formatted_δ)/"
        mkpath(output_dir) # 创建目录如果不存在
        output_path = joinpath(output_dir, "$(formatted_J2).h5")

        h5open(output_path, "w") do f
            write(f, "psi", psi)
        end

        # Update last_psi for the next J2 point
        # This assignment now correctly modifies the global last_psi
        last_psi = psi
    end
end

println("\nZigzag scan complete.")
