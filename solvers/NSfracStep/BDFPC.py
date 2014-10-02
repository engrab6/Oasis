__author__ = "Mikael Mortensen <mikaem@math.uio.no>"
__date__ = "2013-11-07"
__copyright__ = "Copyright (C) 2013 " + __author__
__license__  = "GNU Lesser GPL version 3 or any later version"
"""This is a simplest possible naive implementation of a backwards
differencing solver with pressure correction in rotational form.

The idea is that this solver can be quickly modified and tested for 
alternative implementations. In the end it can be used to validate
the implementations of the more complex optimized solvers.

"""
from dolfin import *
from ..NSfracStep import *
from ..NSfracStep import __all__

def setup(u, q_, q_1, uc_comp, u_components, dt, v, U_AB, u_1, u_2, q_2,
          nu, p_, dp_, mesh, f, fs, q, p, u_, Schmidt,
          scalar_components, Q, **NS_namespace):
    """Set up all equations to be solved."""
    # Implicit Crank Nicolson velocity at t - dt/2
    U_CN = dict((ui, 0.5*(u+q_1[ui])) for ui in uc_comp)

    F = {}
    Fu = {}
    for i, ui in enumerate(u_components):
        # Tentative velocity step
        F[ui] = ((1./(2.*dt))*inner(3*u - 4*q_1[ui] + q_2[ui], v)*dx
                  + inner(inner(2.0*grad(q_1[ui]), u_1) - inner(grad(q_2[ui]), u_2), v)*dx
                  + nu*inner(grad(u), grad(v))*dx + inner(p_.dx(i), v)*dx - inner(f[i], v)*dx)
        
        #F[ui] = ((1./(2.*dt))*inner(3*u - 4*q_1[ui] + q_2[ui], v)*dx
                  #+ inner(dot(U_AB, nabla_grad(U_CN[ui])), v)*dx 
                  #+ nu*inner(grad(u), grad(v))*dx + inner(p_.dx(i), v)*dx - inner(f[i], v)*dx)
            
        # Velocity update
        Fu[ui] = inner(u, v)*dx - inner(q_[ui], v)*dx + (2./3.)*dt*inner(dp_.dx(i), v)*dx

    # Pressure update
    Fp = inner(grad(q), grad(p))*dx + 3./(2.*dt)*div(u_)*q*dx
    
    # reate Function to hold projection of div(u_) on Q
    divu = OasisFunction(div(u_), Q, name="divu")

    # Scalar with SUPG
    h = CellSize(mesh)
    vw = v + h*inner(grad(v), u_)
    n = FacetNormal(mesh)
    for ci in scalar_components:
        F[ci] = ((1./(2.*dt))*inner(3*u - 4*q_1[ci] + q_2[ui], vw)*dx 
                + inner(dot(u, u_), vw)*dx 
                + nu/Schmidt[ci]*inner(grad(u), grad(vw))*dx - inner(fs[ci], vw)*dx) 
                #-nu/Schmidt[ci]*inner(dot(grad(u), n), vw)*ds                 
    
    return dict(F=F, Fu=Fu, Fp=Fp, divu=divu)

def velocity_tentative_solve(ui, F, q_, bcs, x_, b_tmp, udiff, **NS_namespace):
    """Linear algebra solve of tentative velocity component."""
    b_tmp[ui][:] = x_[ui]
    A, L = system(F[ui])
    solve(A == L, q_[ui], bcs[ui])
    udiff[0] += norm(b_tmp[ui] - x_[ui])
    
def pressure_solve(Fp, p_, bcs, dp_, x_, nu, divu, Q, **NS_namespace):
    """Solve pressure equation."""    
    solve(lhs(Fp) == rhs(Fp), dp_, bcs['p'])   
    if bcs['p'] == []:
        normalize(dp_.vector())
    x_["p"].axpy(1, dp_.vector())
    divu()
    x_["p"].axpy(-nu, divu.vector())

def velocity_update(u_components, q_, bcs, Fu, **NS_namespace):
    """Update the velocity after finishing pressure velocity iterations."""
    for ui in u_components:
        solve(lhs(Fu[ui]) == rhs(Fu[ui]), q_[ui], bcs[ui])

def scalar_solve(ci, F, q_, bcs, **NS_namespace):
    """Solve scalar equation."""
    solve(lhs(F[ci]) == rhs(F[ci]), q_[ci], bcs[ci])
