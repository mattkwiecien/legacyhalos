import legacyhalos.sv3 as sv3
import astropy.cosmology


def test_get_cosmology():
    cosmo = sv3.get_cosmology()
    assert isinstance(cosmo, astropy.cosmology.FlatLambdaCDM)

    cosmo = sv3.get_cosmology(WMAP=True)
    assert cosmo.name == "WMAP9"

    cosmo = sv3.get_cosmology(Planck=True)
    assert cosmo.name == "Planck15"
