/*---------------------------------------------------------------------------*\
  cloudHPC template - custom OpenFOAM boundary condition (openfoam.com v2412)
\*---------------------------------------------------------------------------*/

#include "sineWaveFixedValueFvPatchScalarField.H"
#include "addToRunTimeSelectionTable.H"
#include "fvPatchFieldMapper.H"
#include "volFields.H"
#include "mathematicalConstants.H"

// * * * * * * * * * * * * * * * * Constructors  * * * * * * * * * * * * * * //

Foam::sineWaveFixedValueFvPatchScalarField::
sineWaveFixedValueFvPatchScalarField
(
    const fvPatch& p,
    const DimensionedField<scalar, volMesh>& iF
)
:
    fixedValueFvPatchScalarField(p, iF),
    offset_(0),
    amplitude_(0),
    frequency_(0)
{}


Foam::sineWaveFixedValueFvPatchScalarField::
sineWaveFixedValueFvPatchScalarField
(
    const fvPatch& p,
    const DimensionedField<scalar, volMesh>& iF,
    const dictionary& dict
)
:
    fixedValueFvPatchScalarField(p, iF, dict),
    offset_(dict.get<scalar>("offset")),
    amplitude_(dict.get<scalar>("amplitude")),
    frequency_(dict.get<scalar>("frequency"))
{}


Foam::sineWaveFixedValueFvPatchScalarField::
sineWaveFixedValueFvPatchScalarField
(
    const sineWaveFixedValueFvPatchScalarField& ptf,
    const fvPatch& p,
    const DimensionedField<scalar, volMesh>& iF,
    const fvPatchFieldMapper& mapper
)
:
    fixedValueFvPatchScalarField(ptf, p, iF, mapper),
    offset_(ptf.offset_),
    amplitude_(ptf.amplitude_),
    frequency_(ptf.frequency_)
{}


Foam::sineWaveFixedValueFvPatchScalarField::
sineWaveFixedValueFvPatchScalarField
(
    const sineWaveFixedValueFvPatchScalarField& ptf
)
:
    fixedValueFvPatchScalarField(ptf),
    offset_(ptf.offset_),
    amplitude_(ptf.amplitude_),
    frequency_(ptf.frequency_)
{}


Foam::sineWaveFixedValueFvPatchScalarField::
sineWaveFixedValueFvPatchScalarField
(
    const sineWaveFixedValueFvPatchScalarField& ptf,
    const DimensionedField<scalar, volMesh>& iF
)
:
    fixedValueFvPatchScalarField(ptf, iF),
    offset_(ptf.offset_),
    amplitude_(ptf.amplitude_),
    frequency_(ptf.frequency_)
{}


// * * * * * * * * * * * * * * * Member Functions  * * * * * * * * * * * * * //

void Foam::sineWaveFixedValueFvPatchScalarField::updateCoeffs()
{
    if (updated())
    {
        return;
    }

    const scalar t = this->db().time().value();

    operator==
    (
        offset_
      + amplitude_*sin(constant::mathematical::twoPi*frequency_*t)
    );

    fixedValueFvPatchScalarField::updateCoeffs();
}


void Foam::sineWaveFixedValueFvPatchScalarField::write(Ostream& os) const
{
    fvPatchScalarField::write(os);
    os.writeEntry("offset", offset_);
    os.writeEntry("amplitude", amplitude_);
    os.writeEntry("frequency", frequency_);
    fvPatchScalarField::writeValueEntry(os);
}


// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

namespace Foam
{
    makePatchTypeField
    (
        fvPatchScalarField,
        sineWaveFixedValueFvPatchScalarField
    );
}

// ************************************************************************* //
