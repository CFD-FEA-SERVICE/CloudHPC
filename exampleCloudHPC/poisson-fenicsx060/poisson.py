#!/usr/bin/env python3
"""
Poisson problem on the unit square - FEniCSx (DOLFINx) 0.6.0

Solves

    -laplace(u) = f   in  omega = (0, 1) x (0, 1)
              u = u_D on  boundary(omega)

with the manufactured solution u_D = 1 + x^2 + 2y^2, for which f = -6. Because
the exact solution is known, the script reports the L2 and the maximum nodal
error, which makes it a convenient correctness check of the installation and of
the parallel decomposition.

Run it in parallel with

    mpirun -np <N> python3 poisson.py [cells-per-side]

On cloudHPC this is done for you: pick the FEniCSx-0.6.0-r1 script and the
number of vCPU, and the platform launches the file on that many MPI ranks.
"""

import sys

import numpy as np
import ufl
from mpi4py import MPI
from petsc4py.PETSc import ScalarType

from dolfinx import fem, io, mesh
from dolfinx.fem.petsc import LinearProblem

# Cells per side of the unit square; 256 gives ~66k elements and ~33k unknowns
N = int(sys.argv[1]) if len(sys.argv) > 1 else 256


def exact(x):
    return 1.0 + x[0] ** 2 + 2.0 * x[1] ** 2


def main():
    comm = MPI.COMM_WORLD

    domain = mesh.create_unit_square(comm, N, N, mesh.CellType.triangle)
    V = fem.FunctionSpace(domain, ("CG", 1))

    # Dirichlet data on the whole boundary
    u_D = fem.Function(V)
    u_D.interpolate(exact)

    tdim = domain.topology.dim
    fdim = tdim - 1
    domain.topology.create_connectivity(fdim, tdim)
    boundary_facets = mesh.exterior_facet_indices(domain.topology)
    bc = fem.dirichletbc(u_D, fem.locate_dofs_topological(V, fdim, boundary_facets))

    # Variational problem
    u = ufl.TrialFunction(V)
    v = ufl.TestFunction(V)
    f = fem.Constant(domain, ScalarType(-6.0))
    a = ufl.dot(ufl.grad(u), ufl.grad(v)) * ufl.dx
    L = f * v * ufl.dx

    problem = LinearProblem(
        a, L, bcs=[bc],
        petsc_options={"ksp_type": "cg",
                       "pc_type": "gamg",
                       "ksp_rtol": 1.0e-12},
    )
    uh = problem.solve()

    # L2 error against the exact solution, interpolated in a richer space
    V2 = fem.FunctionSpace(domain, ("CG", 2))
    u_ex = fem.Function(V2)
    u_ex.interpolate(exact)
    error_form = fem.form(ufl.inner(uh - u_ex, uh - u_ex) * ufl.dx)
    error_L2 = np.sqrt(comm.allreduce(fem.assemble_scalar(error_form), op=MPI.SUM))

    # Maximum error at the degrees of freedom
    error_max = comm.allreduce(np.max(np.abs(u_D.x.array - uh.x.array)), op=MPI.MAX)

    n_dofs = V.dofmap.index_map.size_global * V.dofmap.index_map_bs
    n_cells = comm.allreduce(domain.topology.index_map(tdim).size_local, op=MPI.SUM)

    if comm.rank == 0:
        print("MPI ranks      : %d" % comm.size)
        print("cells          : %d" % n_cells)
        print("degrees of freedom : %d" % n_dofs)
        print("L2 error       : %.6e" % error_L2)
        print("max nodal error: %.6e" % error_max)

    # Results for ParaView
    with io.XDMFFile(comm, "poisson.xdmf", "w") as xdmf:
        xdmf.write_mesh(domain)
        xdmf.write_function(uh)


if __name__ == "__main__":
    main()
