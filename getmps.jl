using ITensors, ITensorMPS
using HDF5
using Printf

include("hamiltonian.jl")

```
    TFIM
```
# N = 64
# for g in 1.3004:0.01:3.5004
#     # H, sites = eSSH(N, J1=1.0, J2=g, delta=3.0, periodic=false)
#     H, sites = TFIM(N, g)
#     psi0 = randomMPS(sites, 16)
#     nsweeps = 5
#     maxdim = [16, 32, 100, 100, 200]
#     cutoff = 1E-10

#     energy, psi = dmrg(H, psi0, nsweeps=nsweeps, maxdim=maxdim, cutoff=cutoff)
#     formatted_g = @sprintf("%.4f", g)
#     f = h5open("MPStest/TFIM/N$(N)/$(formatted_g).h5", "w")
#     write(f, "psi", psi)
#     close(f)
#     println("g = $g, energy = $energy")
# end

```
    eSSH J2 δ 扫描
```
# for J2 = 0.:0.05:3.
#     for delta = 0.:0.05:4.
#         H, sites = eSSH(N, J1=1.0, J2=J2, delta=delta, periodic=false)
#         psi0 = randomMPS(sites, 16)
#         nsweeps = 5
#         maxdim = [16, 32, 100, 100, 200]
#         cutoff = 1E-10

#         energy, psi = dmrg(H, psi0, nsweeps=nsweeps, maxdim=maxdim, cutoff=cutoff)
#         formatted_J2 = @sprintf("%.4f", J2)
#         formatted_delta = @sprintf("%.4f", delta)
#         f = h5open("MPStest/eSSH/N$(N)/J2$(formatted_J2)/delta$(formatted_delta).h5", "w")
#         write(f, "psi", psi)
#         close(f)
#         println("J2 = $J2, delta = $delta, energy = $energy")
#     end
# end


```
    eSSH 固定 δ 扫描J2
```
N = 128 # 系统大小
# δ = 3.5
# for J2 in vcat(collect(0:0.0005:0.9), collect(0.9:0.0001:1.1), collect(1.1:0.001:3.0))
for δ in [0.0 1.0 1.5 2.0 2.5 3.5 4.0], J2 in 0.0:0.001:3.0
    sites = siteinds("Qubit", N)
    println("J2 = $J2")
    H, sites = eSSH(sites, J1=1.0, J2=J2, delta=δ, periodic=false)
    state = [isodd(i) ? "0" : "1" for i in 1:N]
    psi0 = MPS(sites, state)
    nsweeps = 10
    maxdim = [16, 32, 100, 100, 200]
    cutoff = 1E-10

    energy, psi = dmrg(H, psi0, nsweeps=nsweeps, maxdim=maxdim, cutoff=cutoff)
    formatted_J2 = @sprintf("%.4f", J2)
    output_path = "MPS/eSSH/N$(N)_p_p_old/$(δ)/$(formatted_J2).h5"
    mkpath(dirname(output_path)) # 创建目录如果不存在
    f = h5open(output_path, "w")
    write(f, "psi", psi)
    close(f)
    println("energy = $energy")
end


```
    Cold Atoms Disorder
```
# N = 56
# Ω = 1.0
# for Δ=-2:0.1:2, Rb=2.75:0.1:4.00
#     println("Δ = $Δ, Rb = $Rb")
#     H, sites = cold_atoms(N, Ω, Δ, Rb)
#     psi0 = randomMPS(sites, 16)
#     nsweeps = 5
#     maxdim = [16, 32, 100, 100, 200]
#     cutoff = 1E-10

#     energy, psi = dmrg(H, psi0, nsweeps=nsweeps, maxdim=maxdim, cutoff=cutoff)
#     formatted_Δ = @sprintf("%.4f", Δ)
#     formatted_Rb = @sprintf("%.4f", Rb)
#     f = h5open("MPS/cold_atoms/N$(N)/Δ$(formatted_Δ)_Rb$(formatted_Rb).h5", "w")
#     write(f, "psi", psi)
#     close(f)
#     println("energy = $energy")
# end


# ```    Cluster Ising```
# N = 57
# h2 = 1.5
# # sites = siteinds("Qubit", N)
# # ψ = randomMPS(sites, 16)
# for h1 in -0.445:0.001:1.6
#     println("h1 = $h1")
#     H, sites= clusterIsing(N, h1, h2)
#     state = ["0" for i in 1:N]
#     psi0 = randomMPS(sites, 16)
#     nsweeps = 10
#     maxdim = [16, 32, 100, 100, 200, 200, 200, 200, 200, 200]
#     cutoff = 1E-10

#     energy, psi = dmrg(H, psi0, nsweeps=nsweeps, maxdim=maxdim, cutoff=cutoff)
#     formatted_J2 = @sprintf("%.4f", h1)
#     f = h5open("MPS/clusterising/$(N)_p_p/h21.5/$(formatted_J2).h5", "w")
#     write(f, "psi", psi)
#     close(f)
#     println("energy = $energy")
# end
