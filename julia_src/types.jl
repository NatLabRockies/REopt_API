# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
abstract type TechsExportCurtail end
struct CanExport <: TechsExportCurtail end
struct CanCurtail <: TechsExportCurtail end
struct CanExportAndCurtail <: TechsExportCurtail end
struct CanNotExportCurtail <: TechsExportCurtail end


struct Techs{T <: TechsExportCurtail}
    type::T  # have to use the T parameter
    # names::Array{String, 1}
    # classes::AbstractArray{String, 1}
end


struct Parameter
    t::Techs{T} where {T}
end


# the following goes in utils.jl
ExportTiers = []
TechsCanCurtail = []

if !isempty(ExportTiers)
    if !isempty(TechsCanCurtail)
        techs = Techs(CanExportAndCurtail())
    else
        techs = Techs(CanExport())
    end
else
    if !isempty(TechsCanCurtail)
        techs = Techs(CanCurtail())
    else
        techs = Techs(CanNotExportCurtail())
    end
end

p = Parameter(techs)


# the following will be in reopt.jl
add_constraint(p::Parameter) = add_constraint(p.t)

function add_constraint(::Techs{CanExportAndCurtail}) 
    println("CanExportAndCurtail")
end

function add_constraint(::Techs{CanExport})
    println("CanExport")
end

function add_constraint(::Techs{CanCurtail})
    println("CanCurtail")
end

function add_constraint(::Techs{CanNotExportCurtail}) 
    println("CanNotExportCurtail")
end

add_constraint(p)
