/*---------------------------------------------------------------------------*\
  cloudHPC template - custom OpenFOAM solver (openfoam.com v2412)

Application
    myScalarTransportFoam

Description
    Transient transport of a passive scalar T in a frozen velocity field U,
    with a first-order decay term added as the "custom" part of the physics:

        ddt(T) + div(phi, T) - laplacian(DT, T) = -decayRate*T

    Replace the equation below with your own model. The solver is compiled
    by cloudHPC before the run and selected with "application" in
    system/controlDict.
\*---------------------------------------------------------------------------*/

#include "fvCFD.H"

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

int main(int argc, char *argv[])
{
    argList::addNote
    (
        "Passive scalar transport with first-order decay (cloudHPC template)"
    );

    #include "setRootCase.H"
    #include "createTime.H"
    #include "createMesh.H"
    #include "createFields.H"

    Info<< "\nStarting time loop\n" << endl;

    while (runTime.loop())
    {
        Info<< "Time = " << runTime.timeName() << nl << endl;

        fvScalarMatrix TEqn
        (
            fvm::ddt(T)
          + fvm::div(phi, T)
          - fvm::laplacian(DT, T)
         ==
          - fvm::Sp(decayRate, T)
        );

        TEqn.relax();
        TEqn.solve();

        runTime.write();

        runTime.printExecutionTime(Info);
    }

    Info<< "End\n" << endl;

    return 0;
}

// ************************************************************************* //
