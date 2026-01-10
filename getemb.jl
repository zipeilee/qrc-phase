using ITensors, ITensorMPS
using HDF5
using Printf
using CUDA
using CSV, DataFrames

include("dtc_circuit.jl")
# CUDA.device!(0) #5070Ti
CUDA.device!(1) #3070Ti

```
    eSSH 固定 δ 扫描J2
```
N = 128
δs = [0.5, 3.0, 4.0]
g = 0.84
d= 5
for δ=δs
# for J2 in 0.001:0.002:1.035
# for J2 in 0.940:0.002:3.00 # for 0.5
for J2 in 0.0:0.002:2.898 # for 0.0
    formatted_J2 = @sprintf("%.4f", J2)
    f = h5open("MPS/eSSH/N$(N)_p_p/$(δ)/$(formatted_J2).h5", "r")
    psi = read(f, "psi", MPS)
    embed = real(cu_dtc_circuit(psi, d, g=g))
    # embed = real(get_emb(psi))
    df = DataFrame(column1=embed)
    out_put_path = "data/eSSH/$(N)_p_p/g$(g)_d$(d)/$(δ)/$(formatted_J2).csv"
    mkpath(dirname(out_put_path))
    CSV.write(out_put_path, df)
    println("J2 = $J2")

    # 将psi保存至硬盘
    # out_mps_path = "MPS/eSSH/$(N)_p_p/g$(g)_d$(d)/$(δ)/$(formatted_J2).h5"
    # mkpath(dirname(out_mps_path))
    # h5open(out_mps_path, "w") do f
    #     write(f, "psi", psi)
    # end 

#     psi = nothing
#     embed = nothing
#     df = nothing
    GC.gc()
    CUDA.reclaim()
end
end
