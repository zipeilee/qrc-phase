function measure_zz_mpo(psi)
    N = length(psi)

    os = OpSum()

    for j in 1:N-1
        os += 1.0, "Z", j, "Z", j+1
    end

    H_zz = MPO(os, siteinds(psi))
    zz_expectiation = inner(psi', H_zz, psi)
    return zz_expectiation
end

function measure_zz_corr(psi)
    zzcorr = correlation_matrix(psi, "Z", "Z")
    [zzcorr[i,i+1] for i=1:N-1]
end

function magz(psi)
    magz = expect(psi, "Z")
    totle_mag = sum(magz) / length(psi)
    return totle_mag
end


function string_order_3(psi::MPS)
    sites = siteinds(psi)
    N = length(psi)
    
    op_list = ITensor[]

    push!(op_list, op("Z", sites[1]))

    for i in 4:2:N-2
        push!(op_list, op("X", sites[i]))
    end

    push!(op_list, op("Z", sites[N]))

    reverse!(op_list)

    inner(psi', op_list, psi)
end