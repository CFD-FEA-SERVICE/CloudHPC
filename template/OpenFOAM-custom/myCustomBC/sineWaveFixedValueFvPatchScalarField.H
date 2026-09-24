/*---------------------------------------------------------------------------*\
  cloudHPC template - custom OpenFOAM boundary condition (openfoam.com v2412)

Class
    Foam::sineWaveFixedValueFvPatchScalarField

Description
    Fixed value scalar condition oscillating in time:

        value = offset + amplitude*sin(2*pi*frequency*t)

Usage
    \verbatim
    inlet
    {
        type        sineWaveFixedValue;
        offset      1;
        amplitude   0.5;
        frequency   2;      // Hz
        value       uniform 1;
    }
    \endverbatim

    Load the library in system/controlDict with libs ("libmyCustomBC.so");

SourceFiles
    sineWaveFixedValueFvPatchScalarField.C
\*---------------------------------------------------------------------------*/

#ifndef sineWaveFixedValueFvPatchScalarField_H
#define sineWaveFixedValueFvPatchScalarField_H

#include "fixedValueFvPatchFields.H"

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

namespace Foam
{

class sineWaveFixedValueFvPatchScalarField
:
    public fixedValueFvPatchScalarField
{
    // Private Data

        scalar offset_;
        scalar amplitude_;
        scalar frequency_;


public:

    //- Runtime type information
    TypeName("sineWaveFixedValue");


    // Constructors

        //- Construct from patch and internal field
        sineWaveFixedValueFvPatchScalarField
        (
            const fvPatch&,
            const DimensionedField<scalar, volMesh>&
        );

        //- Construct from patch, internal field and dictionary
        sineWaveFixedValueFvPatchScalarField
        (
            const fvPatch&,
            const DimensionedField<scalar, volMesh>&,
            const dictionary&
        );

        //- Construct by mapping onto a new patch
        sineWaveFixedValueFvPatchScalarField
        (
            const sineWaveFixedValueFvPatchScalarField&,
            const fvPatch&,
            const DimensionedField<scalar, volMesh>&,
            const fvPatchFieldMapper&
        );

        //- Copy construct
        sineWaveFixedValueFvPatchScalarField
        (
            const sineWaveFixedValueFvPatchScalarField&
        );

        //- Copy construct setting internal field reference
        sineWaveFixedValueFvPatchScalarField
        (
            const sineWaveFixedValueFvPatchScalarField&,
            const DimensionedField<scalar, volMesh>&
        );

        //- Return a clone
        virtual tmp<fvPatchScalarField> clone() const
        {
            return tmp<fvPatchScalarField>
            (
                new sineWaveFixedValueFvPatchScalarField(*this)
            );
        }

        //- Clone with an internal field reference
        virtual tmp<fvPatchScalarField> clone
        (
            const DimensionedField<scalar, volMesh>& iF
        ) const
        {
            return tmp<fvPatchScalarField>
            (
                new sineWaveFixedValueFvPatchScalarField(*this, iF)
            );
        }


    // Member Functions

        //- Update the patch value from the current time
        virtual void updateCoeffs();

        //- Write
        virtual void write(Ostream&) const;
};


} // End namespace Foam

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

#endif

// ************************************************************************* //
