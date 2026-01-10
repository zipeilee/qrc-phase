using ITensors, ITensorMPS
using HDF5
using Printf
using CUDA
using CSV, DataFrames
# using ITensors:cpu

include("dtc_circuit.jl")
CUDA.device!(0) #5070Ti
# CUDA.device!(1) #3070Ti
# MPS/clusterising3/57/1.2_1.572.h5

```
    eSSH 固定 δ 扫描J2
```
N = 57
h1s = 0.2:0.2:1.2
g = 0.96
d= 25
for h1=h1s
for h2 in -2.3:0.002:1.6 # for 0.0
    formatted_h1 = @sprintf("%.1f", h1)
    formatted_h2 = @sprintf("%.3f", h2)
    f = h5open("MPS/clusterising3/$(N)/$(formatted_h1)_$(formatted_h2).h5", "r")
    psi = read(f, "psi", MPS)
    _, mps = cu_dtc_circuit!(psi, d, g=g)
    out_put_path = "MPS/clusterising3/$(N)/g$(g)_d$(d)/$(formatted_h1)_$(formatted_h2).h5"
    mkpath(dirname(out_put_path))
    f = h5open(out_put_path, "w")
    write(f, "psi", mps)
    close(f)
    GC.gc()
    CUDA.reclaim()
end
end
