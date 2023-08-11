"""
legacyhalos.sersic
==================

Code to do Sersic on the surface brightness profiles.

"""
import os, pdb
import time, warnings

import numpy as np
import numpy.ma as ma
import matplotlib.pyplot as plt

from astropy.modeling import Fittable2DModel

import legacyhalos.io
from legacyhalos.qa import display_sersic


class SersicSingleWaveModel(Fittable2DModel):
    """
    Define a surface brightness profile model which is three single Sersic
    models connected by a Sersic index and half-light radius which varies
    as a power-law function of wavelength.

    See http://docs.astropy.org/en/stable/modeling/new.html#a-step-by-step-definition-of-a-1-d-gaussian-model
    for useful info.

    """

    from astropy.modeling import Parameter

    nref = Parameter(default=4, bounds=(0.1, 10))
    r50ref = Parameter(default=10, bounds=(0.1, 100))  # [arcsec]
    alpha = Parameter(default=0.0, bounds=(-1, 1))
    beta = Parameter(default=0.0, bounds=(-1, 1))
    mu50_g = Parameter(default=1.0, bounds=(0, 1e4))  # [nanomaggies at r50] [mag=15-30]
    mu50_r = Parameter(default=1.0, bounds=(0, 1e4))
    mu50_z = Parameter(default=1.0, bounds=(0, 1e4))

    linear = False

    def __init__(
        self,
        nref=nref.default,
        r50ref=r50ref.default,
        alpha=alpha.default,
        beta=beta.default,
        mu50_g=mu50_g.default,
        mu50_r=mu50_r.default,
        mu50_z=mu50_z.default,
        psfsigma_g=0.0,
        psfsigma_r=0.0,
        psfsigma_z=0.0,
        lambda_ref=6470,
        lambda_g=4890,
        lambda_r=6470,
        lambda_z=9196,
        pixscale=0.262,
        seed=None,
        maxradius_model=100,
        nradius_model=1001,
        **kwargs
    ):
        """
        maxradius_model in arcsec

        """
        self.band = ("g", "r", "z")

        # from speclite import filters
        # filt = filters.load_filters('decam2014-g', 'decam2014-r', 'decam2014-z')
        # print(filt.effective_wavelengths.value)

        self.lambda_g = lambda_g
        self.lambda_r = lambda_r
        self.lambda_z = lambda_z
        self.lambda_ref = lambda_ref

        self.psfsigma_g = psfsigma_g
        self.psfsigma_r = psfsigma_r
        self.psfsigma_z = psfsigma_z

        self.pixscale = pixscale
        self.seed = seed

        _radius_model = np.linspace(
            0, maxradius_model, nradius_model
        )  # uniformly sampled
        self.radius_model = np.hstack((_radius_model, _radius_model, _radius_model))
        self.wave_model = np.hstack(
            (
                np.repeat(lambda_g, nradius_model),
                np.repeat(lambda_r, nradius_model),
                np.repeat(lambda_z, nradius_model),
            )
        )
        self.sb_model = np.zeros_like(self.wave_model)

        super(SersicSingleWaveModel, self).__init__(
            nref=nref,
            r50ref=r50ref,
            alpha=alpha,
            beta=beta,
            mu50_g=mu50_g,
            mu50_r=mu50_r,
            mu50_z=mu50_z,
            **kwargs
        )

    def get_sersicn(self, nref, lam, alpha):
        return nref * (lam / self.lambda_ref) ** alpha

    def get_r50(self, r50ref, lam, beta):
        return r50ref * (lam / self.lambda_ref) ** beta

    def evaluate(self, r, w, nref, r50ref, alpha, beta, mu50_g, mu50_r, mu50_z):
        """Evaluate the wavelength-dependent single-Sersic model.

        Args:
          r : radius [kpc]
          w : wavelength [Angstrom]
          nref : Sersic index at the reference wavelength lambda_ref
          r50ref : half-light radius at lambda_ref
          alpha : power-law slope for the Sersic index
          beta : power-law slope for the half-light radius
          mu50_g : g-band surface brignthess at r=r50_g
          mu50_r : r-band surface brignthess at r=r50_r
          mu50_z : z-band surface brignthess at r=r50_z

        """
        from scipy.special import gammaincinv
        from scipy.interpolate import interp1d, splev, splrep
        from astropy.convolution import Gaussian1DKernel, convolve

        mu = np.zeros_like(r)

        # Build the surface brightness profile at each wavelength.
        for lam, psfsig, mu50 in zip(
            (self.lambda_g, self.lambda_r, self.lambda_z),
            (self.psfsigma_g, self.psfsigma_r, self.psfsigma_z),
            (mu50_g, mu50_r, mu50_z),
        ):
            n = self.get_sersicn(nref, lam, alpha)
            r50 = self.get_r50(r50ref, lam, beta)

            # evaluate and PSF-convolve the model
            dataindx = w == lam
            modelindx = self.wave_model == lam
            mu_int = mu50 * np.exp(
                -gammaincinv(2 * n, 0.5)
                * ((self.radius_model[modelindx] / r50) ** (1 / n) - 1)
            )

            # convolve the model with the PSF
            if psfsig > 0:
                g = Gaussian1DKernel(stddev=psfsig)  # , mode='linear_interp')
                mu_smooth = convolve(
                    mu_int, g, normalize_kernel=True
                )  # , boundary='extend')
                # fix = (r[indx] > 5 * psfsig * self.pixscale)
                # mu_smooth[fix] = mu_int[fix] # replace with original values
                self.sb_model[modelindx] = mu_smooth
            else:
                self.sb_model[modelindx] = mu_int

            # finally sample the model at the appropriate radii
            # bb = np.interp(r[dataindx], self.radius_model[modelindx], self.sb_model[modelindx])
            # mu[dataindx] = splev(r[dataindx], splrep(self.radius_model[modelindx], self.sb_model[modelindx]))
            # mu[dataindx] = interp1d(self.radius_model[modelindx], self.sb_model[modelindx], kind='cubic')(r[dataindx])
            mu[dataindx] = interp1d(
                self.radius_model[modelindx], mu_smooth, kind="cubic"
            )(r[dataindx])

            # plt.plot(self.radius_model[modelindx], mu_int)
            # plt.plot(self.radius_model[modelindx], mu_smooth)#, s=30, color='orange')
            # plt.scatter(r[dataindx], mu[dataindx], color='k', s=30)
            # plt.yscale('log') ; plt.xscale('log') ; plt.show()
            # plt.yscale('log') ; plt.xlim(0, 3) ; plt.ylim(10, 100) ; plt.show()
            # plt.scatter(r[dataindx], mu[dataindx], color='green', s=30)
            # plt.savefig('junk.png')
            # pdb.set_trace()

        return mu


class SersicExponentialWaveModel(Fittable2DModel):
    """Define a surface brightness profile model which is three Sersic+exponential
    models connected by two Sersic indices and half-light radiii which vary as a
    power-law function of wavelength.

    """

    from astropy.modeling import Parameter

    nref1 = Parameter(default=3, bounds=(0.1, 10))
    nref2 = Parameter(default=1, fixed=True)  # fixed exponential

    r50ref1 = Parameter(default=3, bounds=(0.1, 100))  # [arcsec]
    r50ref2 = Parameter(default=10, bounds=(0.1, 100))  # [arcsec]

    alpha1 = Parameter(default=0.0, bounds=(-1, 1))

    beta1 = Parameter(default=0.0, bounds=(-1, 1))
    beta2 = Parameter(default=0.0)  # , bounds=(-1, 1))

    mu50_g1 = Parameter(default=1.0, bounds=(0, 1e4))
    mu50_r1 = Parameter(default=1.0, bounds=(0, 1e4))
    mu50_z1 = Parameter(default=1.0, bounds=(0, 1e4))

    mu50_g2 = Parameter(default=0.1, bounds=(0, 1e4))
    mu50_r2 = Parameter(default=0.1, bounds=(0, 1e4))
    mu50_z2 = Parameter(default=0.1, bounds=(0, 1e4))

    linear = False

    def __init__(
        self,
        nref1=nref1.default,
        nref2=nref2.default,
        r50ref1=r50ref1.default,
        r50ref2=r50ref2.default,
        alpha1=alpha1.default,
        beta1=beta1.default,
        beta2=beta2.default,
        mu50_g1=mu50_g1.default,
        mu50_r1=mu50_r1.default,
        mu50_z1=mu50_z1.default,
        mu50_g2=mu50_g2.default,
        mu50_r2=mu50_r2.default,
        mu50_z2=mu50_z2.default,
        psfsigma_g=0.0,
        psfsigma_r=0.0,
        psfsigma_z=0.0,
        lambda_ref=6470,
        lambda_g=4890,
        lambda_r=6470,
        lambda_z=9196,
        pixscale=0.262,
        seed=None,
        **kwargs
    ):
        self.band = ("g", "r", "z")

        # from speclite import filters
        # filt = filters.load_filters('decam2014-g', 'decam2014-r', 'decam2014-z')
        # print(filt.effective_wavelengths.value)

        self.lambda_g = lambda_g
        self.lambda_r = lambda_r
        self.lambda_z = lambda_z
        self.lambda_ref = lambda_ref

        self.psfsigma_g = psfsigma_g
        self.psfsigma_r = psfsigma_r
        self.psfsigma_z = psfsigma_z

        self.pixscale = pixscale
        self.seed = seed

        super(SersicExponentialWaveModel, self).__init__(
            nref1=nref1,
            nref2=nref2,
            r50ref1=r50ref1,
            r50ref2=r50ref2,
            alpha1=alpha1,
            beta1=beta1,
            beta2=beta2,
            mu50_g1=mu50_g1,
            mu50_r1=mu50_r1,
            mu50_z1=mu50_z1,
            mu50_g2=mu50_g2,
            mu50_r2=mu50_r2,
            mu50_z2=mu50_z2,
            **kwargs
        )

    def get_sersicn(self, nref, lam, alpha):
        return nref * (lam / self.lambda_ref) ** alpha

    def get_r50(self, r50ref, lam, beta):
        return r50ref * (lam / self.lambda_ref) ** beta

    def evaluate(
        self,
        r,
        w,
        nref1,
        nref2,
        r50ref1,
        r50ref2,
        alpha1,
        beta1,
        beta2,
        mu50_g1,
        mu50_r1,
        mu50_z1,
        mu50_g2,
        mu50_r2,
        mu50_z2,
    ):
        """Evaluate the wavelength-dependent Sersic-exponential model."""
        from scipy.special import gammaincinv
        from astropy.convolution import Gaussian1DKernel, convolve

        mu = np.zeros_like(r)
        n2 = nref2  # fixed exponential

        # Build the surface brightness profile at each wavelength.
        for lam, psfsig, mu50_1, mu50_2 in zip(
            (self.lambda_g, self.lambda_r, self.lambda_z),
            (self.psfsigma_g, self.psfsigma_r, self.psfsigma_z),
            (mu50_g1, mu50_r1, mu50_z1),
            (mu50_g2, mu50_r2, mu50_z2),
        ):
            n1 = self.get_sersicn(nref1, lam, alpha1)
            r50_1 = self.get_r50(r50ref1, lam, beta1)
            r50_2 = self.get_r50(r50ref2, lam, beta2)

            indx = w == lam
            if np.sum(indx) > 0:
                mu_int = mu50_1 * np.exp(
                    -gammaincinv(2 * n1, 0.5) * ((r[indx] / r50_1) ** (1 / n1) - 1)
                ) + mu50_2 * np.exp(
                    -gammaincinv(2 * n2, 0.5) * ((r[indx] / r50_2) ** (1 / n2) - 1)
                )

                # smooth with the PSF
                if psfsig > 0:
                    g = Gaussian1DKernel(stddev=psfsig)  # , mode='linear_interp')
                    mu_smooth = convolve(
                        mu_int, g, normalize_kernel=True, boundary="extend"
                    )
                    # fix = (r[indx] > 5 * psfsig * self.pixscale)
                    # mu_smooth[fix] = mu_int[fix] # replace with original values
                    mu[indx] = mu_smooth
                else:
                    mu[indx] = mu_int

        return mu


class SersicDoubleWaveModel(Fittable2DModel):
    """
    Define a surface brightness profile model which is three double Sersic
    models connected by two Sersic indices and half-light radiii which vary
    as a power-law function of wavelength.

    """

    from astropy.modeling import Parameter

    nref1 = Parameter(default=3, bounds=(0.1, 8))
    nref2 = Parameter(default=1, bounds=(0.1, 8))

    r50ref1 = Parameter(default=3, bounds=(0.1, 100))  # [arcsec]
    r50ref2 = Parameter(default=10, bounds=(0.1, 100))  # [arcsec]

    alpha1 = Parameter(default=0.0, bounds=(-1, 1))
    alpha2 = Parameter(default=0.0)  # , bounds=(-1, 1))

    beta1 = Parameter(default=0.0, bounds=(-1, 1))
    beta2 = Parameter(default=0.0)  # , bounds=(-1, 1))

    mu50_g1 = Parameter(default=1.0, bounds=(0, 1e4))
    mu50_r1 = Parameter(default=1.0, bounds=(0, 1e4))
    mu50_z1 = Parameter(default=1.0, bounds=(0, 1e4))

    mu50_g2 = Parameter(default=0.1, bounds=(0, 1e4))
    mu50_r2 = Parameter(default=0.1, bounds=(0, 1e4))
    mu50_z2 = Parameter(default=0.1, bounds=(0, 1e4))

    linear = False

    def __init__(
        self,
        nref1=nref1.default,
        nref2=nref2.default,
        r50ref1=r50ref1.default,
        r50ref2=r50ref2.default,
        alpha1=alpha1.default,
        alpha2=alpha2.default,
        beta1=beta1.default,
        beta2=beta2.default,
        mu50_g1=mu50_g1.default,
        mu50_r1=mu50_r1.default,
        mu50_z1=mu50_z1.default,
        mu50_g2=mu50_g2.default,
        mu50_r2=mu50_r2.default,
        mu50_z2=mu50_z2.default,
        psfsigma_g=0.0,
        psfsigma_r=0.0,
        psfsigma_z=0.0,
        lambda_ref=6470,
        lambda_g=4890,
        lambda_r=6470,
        lambda_z=9196,
        pixscale=0.262,
        seed=None,
        **kwargs
    ):
        self.band = ("g", "r", "z")

        # from speclite import filters
        # filt = filters.load_filters('decam2014-g', 'decam2014-r', 'decam2014-z')
        # print(filt.effective_wavelengths.value)

        self.lambda_g = lambda_g
        self.lambda_r = lambda_r
        self.lambda_z = lambda_z
        self.lambda_ref = lambda_ref

        self.psfsigma_g = psfsigma_g
        self.psfsigma_r = psfsigma_r
        self.psfsigma_z = psfsigma_z

        self.pixscale = pixscale
        self.seed = seed

        super(SersicDoubleWaveModel, self).__init__(
            nref1=nref1,
            nref2=nref2,
            r50ref1=r50ref1,
            r50ref2=r50ref2,
            alpha1=alpha1,
            alpha2=alpha2,
            beta1=beta1,
            beta2=beta2,
            mu50_g1=mu50_g1,
            mu50_r1=mu50_r1,
            mu50_z1=mu50_z1,
            mu50_g2=mu50_g2,
            mu50_r2=mu50_r2,
            mu50_z2=mu50_z2,
            **kwargs
        )

    def get_sersicn(self, nref, lam, alpha):
        return nref * (lam / self.lambda_ref) ** alpha

    def get_r50(self, r50ref, lam, beta):
        return r50ref * (lam / self.lambda_ref) ** beta

    def evaluate(
        self,
        r,
        w,
        nref1,
        nref2,
        r50ref1,
        r50ref2,
        alpha1,
        alpha2,
        beta1,
        beta2,
        mu50_g1,
        mu50_r1,
        mu50_z1,
        mu50_g2,
        mu50_r2,
        mu50_z2,
    ):
        """Evaluate the wavelength-dependent double-Sersic model."""
        from scipy.special import gammaincinv
        from astropy.convolution import Gaussian1DKernel, convolve

        mu = np.zeros_like(r)

        # Build the surface brightness profile at each wavelength.
        for lam, psfsig, mu50_1, mu50_2 in zip(
            (self.lambda_g, self.lambda_r, self.lambda_z),
            (self.psfsigma_g, self.psfsigma_r, self.psfsigma_z),
            (mu50_g1, mu50_r1, mu50_z1),
            (mu50_g2, mu50_r2, mu50_z2),
        ):
            n1 = self.get_sersicn(nref1, lam, alpha1)
            n2 = self.get_sersicn(nref2, lam, alpha2)
            r50_1 = self.get_r50(r50ref1, lam, beta1)
            r50_2 = self.get_r50(r50ref2, lam, beta2)

            indx = w == lam
            if np.sum(indx) > 0:
                mu_int = mu50_1 * np.exp(
                    -gammaincinv(2 * n1, 0.5) * ((r[indx] / r50_1) ** (1 / n1) - 1)
                ) + mu50_2 * np.exp(
                    -gammaincinv(2 * n2, 0.5) * ((r[indx] / r50_2) ** (1 / n2) - 1)
                )

                # smooth with the PSF
                if psfsig > 0:
                    g = Gaussian1DKernel(stddev=psfsig)  # , mode='linear_interp')#,
                    mu_smooth = convolve(
                        mu_int, g, normalize_kernel=True, boundary="extend"
                    )

                    # import matplotlib.pyplot as plt
                    # plt.plot(r[indx], mu_smooth/mu_int) ; plt.show()
                    # plt.plot(r[indx], mu_int) ; plt.plot(r[indx], mu_smooth) ; plt.yscale('log') ; plt.show()
                    # pdb.set_trace()

                    # fix = (r[indx] > 5 * psfsig * self.pixscale)
                    # mu_smooth[fix] = mu_int[fix] # replace with original values
                    mu[indx] = mu_smooth
                else:
                    mu[indx] = mu_int

        return mu


class SersicTripleWaveModel(Fittable2DModel):
    """Define a surface brightness profile model which is three triple-Sersic models
    connected by three Sersic indices and half-light radiii which vary
    (optionally) as a power-law function of wavelength.

    """

    from astropy.modeling import Parameter

    nref1 = Parameter(default=3, bounds=(0.1, 8))
    nref2 = Parameter(default=1, bounds=(0.1, 8))
    nref3 = Parameter(default=1, bounds=(0.1, 8))

    r50ref1 = Parameter(default=1, bounds=(0.1, 100))  # [arcsec]
    r50ref2 = Parameter(default=10, bounds=(0.1, 100))  # [arcsec]
    r50ref3 = Parameter(default=30, bounds=(0.1, 100))  # [arcsec]

    alpha1 = Parameter(default=0.0, bounds=(-1, 1))
    alpha2 = Parameter(default=0.0)  # , bounds=(-1, 1))
    alpha3 = Parameter(default=0.0)  # , bounds=(-1, 1))

    beta1 = Parameter(default=0.0, bounds=(-1, 1))
    beta2 = Parameter(default=0.0)  # , bounds=(-1, 1))
    beta3 = Parameter(default=0.0)  # , bounds=(-1, 1))

    mu50_g1 = Parameter(default=1.0, bounds=(0, 1e4))
    mu50_r1 = Parameter(default=1.0, bounds=(0, 1e4))
    mu50_z1 = Parameter(default=1.0, bounds=(0, 1e4))

    mu50_g2 = Parameter(default=0.1, bounds=(0, 1e4))
    mu50_r2 = Parameter(default=0.1, bounds=(0, 1e4))
    mu50_z2 = Parameter(default=0.1, bounds=(0, 1e4))

    mu50_g3 = Parameter(default=0.05, bounds=(0, 1e4))
    mu50_r3 = Parameter(default=0.05, bounds=(0, 1e4))
    mu50_z3 = Parameter(default=0.05, bounds=(0, 1e4))

    linear = False

    def __init__(
        self,
        nref1=nref1.default,
        nref2=nref2.default,
        nref3=nref3.default,
        r50ref1=r50ref1.default,
        r50ref2=r50ref2.default,
        r50ref3=r50ref3.default,
        alpha1=alpha1.default,
        alpha2=alpha2.default,
        alpha3=alpha3.default,
        beta1=beta1.default,
        beta2=beta2.default,
        beta3=beta3.default,
        mu50_g1=mu50_g1.default,
        mu50_r1=mu50_r1.default,
        mu50_z1=mu50_z1.default,
        mu50_g2=mu50_g2.default,
        mu50_r2=mu50_r2.default,
        mu50_z2=mu50_z2.default,
        mu50_g3=mu50_g3.default,
        mu50_r3=mu50_r3.default,
        mu50_z3=mu50_z3.default,
        psfsigma_g=0.0,
        psfsigma_r=0.0,
        psfsigma_z=0.0,
        lambda_ref=6470,
        lambda_g=4890,
        lambda_r=6470,
        lambda_z=9196,
        pixscale=0.262,
        seed=None,
        **kwargs
    ):
        self.band = ("g", "r", "z")

        # from speclite import filters
        # filt = filters.load_filters('decam2014-g', 'decam2014-r', 'decam2014-z')
        # print(filt.effective_wavelengths.value)

        self.lambda_g = lambda_g
        self.lambda_r = lambda_r
        self.lambda_z = lambda_z
        self.lambda_ref = lambda_ref

        self.psfsigma_g = psfsigma_g
        self.psfsigma_r = psfsigma_r
        self.psfsigma_z = psfsigma_z

        self.pixscale = pixscale
        self.seed = seed

        super(SersicTripleWaveModel, self).__init__(
            nref1=nref1,
            nref2=nref2,
            nref3=nref3,
            r50ref1=r50ref1,
            r50ref2=r50ref2,
            r50ref3=r50ref3,
            alpha1=alpha1,
            alpha2=alpha2,
            alpha3=alpha3,
            beta1=beta1,
            beta2=beta2,
            beta3=beta3,
            mu50_g1=mu50_g1,
            mu50_r1=mu50_r1,
            mu50_z1=mu50_z1,
            mu50_g2=mu50_g2,
            mu50_r2=mu50_r2,
            mu50_z2=mu50_z2,
            mu50_g3=mu50_g3,
            mu50_r3=mu50_r3,
            mu50_z3=mu50_z3,
            **kwargs
        )

    def get_sersicn(self, nref, lam, alpha):
        return nref * (lam / self.lambda_ref) ** alpha

    def get_r50(self, r50ref, lam, beta):
        return r50ref * (lam / self.lambda_ref) ** beta

    def evaluate(
        self,
        r,
        w,
        nref1,
        nref2,
        nref3,
        r50ref1,
        r50ref2,
        r50ref3,
        alpha1,
        alpha2,
        alpha3,
        beta1,
        beta2,
        beta3,
        mu50_g1,
        mu50_r1,
        mu50_z1,
        mu50_g2,
        mu50_r2,
        mu50_z2,
        mu50_g3,
        mu50_r3,
        mu50_z3,
    ):
        """Evaluate the wavelength-dependent double-Sersic model."""
        from scipy.special import gammaincinv
        from astropy.convolution import Gaussian1DKernel, convolve

        mu = np.zeros_like(r)

        # Build the surface brightness profile at each wavelength.
        for lam, psfsig, mu50_1, mu50_2, mu50_3 in zip(
            (self.lambda_g, self.lambda_r, self.lambda_z),
            (self.psfsigma_g, self.psfsigma_r, self.psfsigma_z),
            (mu50_g1, mu50_r1, mu50_z1),
            (mu50_g2, mu50_r2, mu50_z2),
            (mu50_g3, mu50_r3, mu50_z3),
        ):
            n1 = self.get_sersicn(nref1, lam, alpha1)
            n2 = self.get_sersicn(nref2, lam, alpha2)
            n3 = self.get_sersicn(nref3, lam, alpha3)
            r50_1 = self.get_r50(r50ref1, lam, beta1)
            r50_2 = self.get_r50(r50ref2, lam, beta2)
            r50_3 = self.get_r50(r50ref3, lam, beta3)

            indx = w == lam
            if np.sum(indx) > 0:
                mu_int = (
                    mu50_1
                    * np.exp(
                        -gammaincinv(2 * n1, 0.5) * ((r[indx] / r50_1) ** (1 / n1) - 1)
                    )
                    + mu50_2
                    * np.exp(
                        -gammaincinv(2 * n2, 0.5) * ((r[indx] / r50_2) ** (1 / n2) - 1)
                    )
                    + mu50_3
                    * np.exp(
                        -gammaincinv(2 * n3, 0.5) * ((r[indx] / r50_3) ** (1 / n3) - 1)
                    )
                )

                # smooth with the PSF
                if psfsig > 0:
                    g = Gaussian1DKernel(stddev=psfsig)  # , mode='linear_interp')#,
                    mu_smooth = convolve(
                        mu_int, g, normalize_kernel=True, boundary="extend"
                    )

                    # import matplotlib.pyplot as plt
                    # plt.plot(r[indx], mu_smooth/mu_int) ; plt.show()
                    # plt.plot(r[indx], mu_int) ; plt.plot(r[indx], mu_smooth) ; plt.yscale('log') ; plt.show()
                    # pdb.set_trace()

                    # fix = (r[indx] > 5 * psfsig * self.pixscale)
                    # mu_smooth[fix] = mu_int[fix] # replace with original values
                    mu[indx] = mu_smooth
                else:
                    mu[indx] = mu_int

        return mu


class SersicWaveFit(object):
    def __init__(
        self,
        ellipsefit,
        seed=None,
        minerr=0.01,
        nradius_uniform=150,
        snrmin=1,
        nball=10,
        chi2fail=1e6,
    ):
        from scipy.interpolate import splev, splrep
        from astropy.modeling import fitting

        self.rand = np.random.RandomState(seed)

        # initialize the fitter
        self.fitter = fitting.LevMarLSQFitter()

        refband, pixscale, redshift = (
            ellipsefit["refband"],
            ellipsefit["pixscale"],
            ellipsefit["redshift"],
        )

        # parse the input sbprofile into the format that SersicSingleWaveModel()
        # expects
        sb, sberr, wave, radius = [], [], [], []
        # sb_uniform, sberr_uniform, wave_uniform, radius_uniform = [], [], [], []
        for band, lam in zip(
            self.initfit.band,
            (self.initfit.lambda_g, self.initfit.lambda_r, self.initfit.lambda_z),
        ):
            # any quality cuts on stop_code here?!?
            # rad = ellipsefit[band].sma * pixscale # semi-major axis [arcsec]

            # Compute the circularized radius [arcsec] and add the minimum uncertainty in quadrature.
            # _radius = ellipsefit[band].sma * pixscale
            _radius = (
                ellipsefit[band].sma * np.sqrt(1 - ellipsefit[band].eps) * pixscale
            )  # [arcsec]
            _sb = ellipsefit[band].intens
            _sberr = np.sqrt(
                ellipsefit[band].int_err ** 2 + (0.4 * np.log(10) * _sb * minerr) ** 2
            )

            # print('Uniform weights!')
            # _sberr = np.zeros_like(_sb) + 0.05

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                keep = np.isfinite(_sb) * (_sb / _sberr > snrmin)
            print(
                "Keeping {} / {} measurements in band {}".format(
                    np.sum(keep), len(_radius), band
                )
            )

            _radius = _radius[keep]
            _sb = _sb[keep]
            _sberr = _sberr[keep]

            radius.append(_radius)
            sb.append(_sb)
            sberr.append(_sberr)
            wave.append(np.repeat(lam, len(_radius)))

            # Interpolate onto a regular radius grid (in arcsec!).  We
            # interpolate the uncertainties linearly and use a b-spline
            # interpolation of the surface brightness profile to be able to
            # smoothly connect missing measurements at large radii.  Note that
            # higher-order interpolation of the uncertainties (or variances) is
            # not well-behaved.
            if False:
                _radius_uniform = np.linspace(
                    _radius.min(), _radius.max(), nradius_uniform
                )
                try:
                    _sb_uniform = splev(
                        _radius_uniform, splrep(_radius, _sb, w=1 / _sberr)
                    )
                except:
                    _sb_uniform = np.interp(_radius_uniform, _radius, _sb)
                _sberr_uniform = np.sqrt(
                    np.interp(_radius_uniform, _radius, _sberr**2)
                )

                radius_uniform.append(_radius_uniform)
                sb_uniform.append(_sb_uniform)
                sberr_uniform.append(_sberr_uniform)
                wave_uniform.append(np.repeat(lam, len(_radius_uniform)))

                if False:  # QA
                    fig, ax = plt.subplots(2, 1, sharex=True)
                    ax[0].scatter(_radius, _sb)
                    ax[0].plot(_radius_uniform, _sb_uniform, color="orange", alpha=0.5)
                    ax[1].scatter(_radius, _sberr)
                    ax[1].plot(
                        _radius_uniform, _sberr_uniform, color="orange", alpha=0.5
                    )
                    for xx in ax:
                        xx.set_yscale("log")
                        xx.set_xscale("log")
                    plt.show()

        self.sb = np.hstack(sb)
        self.sberr = np.hstack(sberr)
        self.wave = np.hstack(wave)
        self.radius = np.hstack(radius)

        # self.sb_uniform = np.hstack(sb_uniform)
        # self.sberr_uniform = np.hstack(sberr_uniform)
        # self.wave_uniform = np.hstack(wave_uniform)
        # self.radius_uniform = np.hstack(radius_uniform)

        self.redshift = redshift
        self.minerr = minerr
        self.pixscale = pixscale
        self.seed = seed

        self.nball = nball
        self.chi2fail = chi2fail

    def chi2(self, bestfit):
        dof = len(self.sb) - len(bestfit.parameters)
        sbmodel = bestfit(self.radius, self.wave)
        chi2 = np.sum((self.sb - sbmodel) ** 2 / self.sberr**2) / dof

        if False:
            dof = len(self.sb_uniform) - len(bestfit.parameters)
            sbmodel = bestfit(self.radius_uniform, self.wave_uniform)
            chi2 = (
                np.sum((self.sb_uniform - sbmodel) ** 2 / self.sberr_uniform**2) / dof
            )
        return chi2

    def _fit(self, verbose=False, modeltype="single"):
        """Perform the chi2 minimization."""
        import warnings

        if verbose:
            warnvalue = "always"
        else:
            warnvalue = "ignore"

        # initialize the output dictionary
        result = {
            "success": False,
            "converged": False,
            "redshift": self.redshift,
            "modeltype": modeltype,
            "radius": self.radius,
            "wave": self.wave,
            "sb": self.sb,
            "sberr": self.sberr,
            #'radius_uniform': self.radius_uniform,
            #'wave_uniform': self.wave_uniform,
            #'sb_uniform': self.sb_uniform,
            #'sberr_uniform': self.sberr_uniform,
            "band": self.initfit.band,
            "lambda_ref": self.initfit.lambda_ref,
            "lambda_g": self.initfit.lambda_g,
            "lambda_r": self.initfit.lambda_r,
            "lambda_z": self.initfit.lambda_z,
            "params": self.initfit.param_names,
            "chi2": self.chi2fail,  # initial value
            "dof": len(self.sb) - len(self.initfit.parameters),
            "minerr": self.minerr,
            "pixscale": self.pixscale,
            "seed": self.seed,
        }

        # perturb the parameter values
        nparams = len(self.initfit.parameters)
        params = np.repeat(self.initfit.parameters, self.nball).reshape(
            nparams, self.nball
        )
        for ii, pp in enumerate(self.initfit.param_names):
            pinfo = getattr(self.initfit, pp)
            if not pinfo.fixed:  # don't touch fixed parameters
                if pinfo.bounds[0] is not None:
                    # params[ii, :] = self.rand.uniform(pinfo.bounds[0], pinfo.bounds[1], self.nball)
                    if pinfo.default == 0:
                        scale = 0.1 * (pinfo.bounds[1] - pinfo.bounds[0])
                    else:
                        scale = 0.2 * pinfo.default
                    params[ii, :] += self.rand.normal(scale=scale, size=self.nball)
                    toosmall = np.where(params[ii, :] < pinfo.bounds[0])[0]
                    if len(toosmall) > 0:
                        params[ii, toosmall] = pinfo.default
                    toobig = np.where(params[ii, :] > pinfo.bounds[1])[0]
                    if len(toobig) > 0:
                        params[ii, toobig] = pinfo.default
                    # if ii == 2:
                    #    print(params[ii, :])
                    #    pdb.set_trace()
                else:
                    params[ii, :] += self.rand.normal(
                        scale=0.2 * pinfo.default, size=self.nball
                    )
        # print(params)
        # pdb.set_trace()

        # perform the fit nball times
        with warnings.catch_warnings():
            warnings.simplefilter(warnvalue)

            chi2 = np.zeros(self.nball) + self.chi2fail
            for jj in range(self.nball):
                self.initfit.parameters = params[:, jj]
                # ballfit = self.fitter(self.initfit, self.radius_uniform, self.wave_uniform,
                #                      self.sb_uniform, weights=1/self.sberr_uniform, maxiter=200)
                ballfit = self.fitter(
                    self.initfit,
                    self.radius,
                    self.wave,
                    self.sb,
                    weights=1 / self.sberr,
                    maxiter=200,
                )
                chi2[jj] = self.chi2(ballfit)
                if self.fitter.fit_info["param_cov"] is None:  # failed
                    if verbose:
                        print(jj, self.fitter.fit_info["message"], chi2[jj])
                else:
                    params[:, jj] = ballfit.parameters  # update

        # did at least one fit succeed?
        good = chi2 < self.chi2fail
        if np.sum(good) == 0:
            print("{}-Sersic fitting failed.".format(modeltype.upper()))
            result.update({"fit_message": self.fitter.fit_info["message"]})
            return result

        # otherwise, re-evaluate the model at the chi2 minimum
        result["success"] = True
        mindx = np.argmin(chi2)

        self.initfit.parameters = params[:, mindx]
        # bestfit = self.fitter(self.initfit, self.radius_uniform, self.wave_uniform,
        #                      self.sb_uniform, weights=1/self.sberr_uniform)
        bestfit = self.fitter(
            self.initfit, self.radius, self.wave, self.sb, weights=1 / self.sberr
        )
        minchi2 = chi2[mindx]
        print(
            "{} Sersic fitting succeeded with a chi^2 minimum of {:.2f}".format(
                modeltype.upper(), minchi2
            )
        )

        ## Integrate the data and model over various apertures.
        # phot = self.integrate(bestfit)

        # Pack the results in a dictionary and return.
        # https://gist.github.com/eteq/1f3f0cec9e4f27536d52cd59054c55f2
        if self.fitter.fit_info["param_cov"] is not None:
            cov = self.fitter.fit_info["param_cov"]
            unc = np.diag(cov) ** 0.5
            result["converged"] = True
        else:
            cov = np.zeros((nparams, nparams))
            unc = np.zeros(nparams)

        count = 0
        for ii, pp in enumerate(bestfit.param_names):
            pinfo = getattr(bestfit, pp)
            result.update({bestfit.param_names[ii]: bestfit.parameters[ii]})
            if pinfo.fixed:
                result.update({bestfit.param_names[ii] + "_err": 0.0})
            elif pinfo.tied:
                pass  # hack! see https://github.com/astropy/astropy/issues/7202
            else:
                result.update({bestfit.param_names[ii] + "_err": unc[count]})
                count += 1

        # Fix the uncertainties of tied parameters.  Very hacky here!
        if "alpha2" in bestfit.param_names and "alpha1" in bestfit.param_names:
            if bestfit.alpha2.tied is not False:
                result.update({"alpha2_err": result["alpha1_err"]})
        if "alpha3" in bestfit.param_names and "alpha1" in bestfit.param_names:
            if bestfit.alpha3.tied is not False:
                result.update({"alpha3_err": result["alpha1_err"]})
        if "beta2" in bestfit.param_names and "beta1" in bestfit.param_names:
            if bestfit.beta2.tied is not False:
                result.update({"beta2_err": result["beta1_err"]})
        if "beta3" in bestfit.param_names and "beta1" in bestfit.param_names:
            if bestfit.beta3.tied is not False:
                result.update({"beta3_err": result["beta1_err"]})

        result["chi2"] = minchi2
        result.update(
            {
                #'values': bestfit.parameters,
                #'uncertainties': np.diag(cov)**0.5,
                "cov": cov,
                "bestfit": bestfit,
                "fit_message": self.fitter.fit_info["message"],
                #'phot': phot,
            }
        )

        return result


class SersicSingleWaveFit(SersicWaveFit):
    """Fit surface brightness profiles with the SersicSingleWaveModel model."""

    def __init__(
        self,
        ellipsefit,
        minerr=0.01,
        snrmin=1,
        nball=10,
        fix_alpha=False,
        fix_beta=False,
        seed=None,
        modeltype="single",
    ):
        self.modeltype = modeltype
        self.fixed = {"alpha": fix_alpha, "beta": fix_beta}
        self.initfit = SersicSingleWaveModel(
            fixed=self.fixed,
            psfsigma_g=ellipsefit["psfsigma_g"],
            psfsigma_r=ellipsefit["psfsigma_r"],
            psfsigma_z=ellipsefit["psfsigma_z"],
            pixscale=ellipsefit["pixscale"],
            seed=seed,
        )

        super(SersicSingleWaveFit, self).__init__(
            ellipsefit, seed=seed, snrmin=snrmin, nball=nball
        )

    def fit(self, verbose=False):
        return self._fit(verbose=verbose, modeltype=self.modeltype)


class SersicExponentialWaveFit(SersicWaveFit):
    """Fit surface brightness profiles with the SersicExponentialWaveModel model."""

    def __init__(
        self,
        ellipsefit,
        minerr=0.01,
        snrmin=1,
        nball=10,
        fix_alpha=False,
        fix_beta=False,
        seed=None,
        modeltype="exponential",
    ):
        self.modeltype = modeltype
        self.fixed = {"alpha1": fix_alpha, "beta1": fix_beta, "beta2": fix_beta}
        # tied = {'r50ref2': self.tie_r50ref2}
        tied = {"beta2": self.tie_beta2}

        self.initfit = SersicExponentialWaveModel(
            fixed=self.fixed,
            tied=tied,
            psfsigma_g=ellipsefit["psfsigma_g"],
            psfsigma_r=ellipsefit["psfsigma_r"],
            psfsigma_z=ellipsefit["psfsigma_z"],
            pixscale=ellipsefit["pixscale"],
            seed=seed,
        )

        super(SersicExponentialWaveFit, self).__init__(
            ellipsefit, seed=seed, snrmin=snrmin, nball=nball
        )

    def tie_beta2(self, model):
        return model.beta1

    def tie_r50ref2(self, model):
        if model.r50ref2 < model.r50ref1:
            return model.r50ref1 * 1.05

    def fit(self, verbose=False):
        return self._fit(verbose=verbose, modeltype=self.modeltype)


class SersicDoubleWaveFit(SersicWaveFit):
    """Fit surface brightness profiles with the SersicDoubleWaveModel model."""

    def __init__(
        self,
        ellipsefit,
        minerr=0.01,
        snrmin=1,
        nball=10,
        fix_alpha=False,
        fix_beta=False,
        seed=None,
        modeltype="double",
    ):
        self.modeltype = modeltype
        self.fixed = {
            "alpha1": fix_alpha,
            "alpha2": fix_alpha,
            "beta1": fix_beta,
            "beta2": fix_beta,
        }
        tied = {"alpha2": self.tie_alpha2, "beta2": self.tie_beta2}

        self.initfit = SersicDoubleWaveModel(
            fixed=self.fixed,
            tied=tied,
            psfsigma_g=ellipsefit["psfsigma_g"],
            psfsigma_r=ellipsefit["psfsigma_r"],
            psfsigma_z=ellipsefit["psfsigma_z"],
            pixscale=ellipsefit["pixscale"],
            seed=seed,
        )

        super(SersicDoubleWaveFit, self).__init__(
            ellipsefit, seed=seed, snrmin=snrmin, nball=nball
        )

    def tie_alpha2(self, model):
        return model.alpha1

    def tie_beta2(self, model):
        return model.beta1

    def fit(self, verbose=False):
        return self._fit(verbose=verbose, modeltype=self.modeltype)


class SersicTripleWaveFit(SersicWaveFit):
    """Fit surface brightness profiles with the SersicTripleWaveModel model."""

    def __init__(
        self,
        ellipsefit,
        minerr=0.01,
        snrmin=1,
        nball=10,
        fix_alpha=False,
        fix_beta=False,
        seed=None,
        modeltype="triple",
    ):
        self.modeltype = modeltype
        self.fixed = {
            "alpha1": fix_alpha,
            "alpha2": fix_alpha,
            "alpha3": fix_alpha,
            "beta1": fix_beta,
            "beta2": fix_beta,
            "beta3": fix_beta,
        }
        tied = {
            "alpha2": self.tie_alpha2,
            "alpha3": self.tie_alpha3,
            "beta2": self.tie_beta2,
            "beta3": self.tie_beta3,
        }

        self.initfit = SersicTripleWaveModel(
            fixed=self.fixed,
            tied=tied,
            psfsigma_g=ellipsefit["psfsigma_g"],
            psfsigma_r=ellipsefit["psfsigma_r"],
            psfsigma_z=ellipsefit["psfsigma_z"],
            pixscale=ellipsefit["pixscale"],
            seed=seed,
        )

        super(SersicTripleWaveFit, self).__init__(
            ellipsefit, seed=seed, snrmin=snrmin, nball=nball
        )

    def tie_alpha2(self, model):
        return model.alpha1

    def tie_alpha3(self, model):
        return model.alpha1

    def tie_beta2(self, model):
        return model.beta1

    def tie_beta3(self, model):
        return model.beta1

    def fit(self, verbose=False):
        return self._fit(verbose=verbose, modeltype=self.modeltype)


def sersic_single(
    galaxy,
    galaxydir,
    ellipsefit,
    minerr=0.01,
    snrmin=1,
    nball=20,
    seed=None,
    debug=False,
    nowavepower=False,
    nowrite=False,
    verbose=False,
):
    """Wrapper to fit a single Sersic model to an input surface brightness profile.

    nowavepower : no wavelength-dependent variation in the Sersic index or
      half-light radius

    """
    if nowavepower:
        modeltype = "single-nowavepower"
        sersic = SersicSingleWaveFit(
            ellipsefit,
            minerr=minerr,
            snrmin=snrmin,
            nball=nball,
            fix_alpha=True,
            fix_beta=True,
            seed=seed,
            modeltype=modeltype,
        )
    else:
        modeltype = "single"
        sersic = SersicSingleWaveFit(
            ellipsefit,
            minerr=minerr,
            snrmin=snrmin,
            nball=nball,
            fix_alpha=False,
            fix_beta=False,
            seed=seed,
            modeltype=modeltype,
        )

    sersic = sersic.fit(verbose=verbose)

    if debug:
        display_sersic(sersic)

    if not nowrite:
        legacyhalos.io.write_sersic(
            galaxy, galaxydir, sersic, modeltype=modeltype, verbose=verbose
        )

    return sersic


def sersic_exponential(
    galaxy,
    galaxydir,
    ellipsefit,
    minerr=0.01,
    snrmin=1,
    nball=20,
    seed=None,
    debug=False,
    nowavepower=False,
    nowrite=False,
    verbose=False,
):
    """Wrapper to fit a Sersic+exponential model to an input surface brightness
    profile.

    nowavepower : no wavelength-dependent variation in the Sersic index or
      half-light radius

    """
    if nowavepower:
        modeltype = "exponential-nowavepower"
        sersic = SersicExponentialWaveFit(
            ellipsefit,
            minerr=minerr,
            snrmin=snrmin,
            nball=nball,
            fix_alpha=True,
            fix_beta=True,
            seed=seed,
            modeltype=modeltype,
        )
    else:
        modeltype = "exponential"
        sersic = SersicExponentialWaveFit(
            ellipsefit,
            minerr=minerr,
            snrmin=snrmin,
            nball=nball,
            fix_alpha=False,
            fix_beta=False,
            seed=seed,
            modeltype=modeltype,
        )

    sersic = sersic.fit(verbose=verbose)

    if debug:
        display_sersic(sersic)  # , png='junk.png')
    # pdb.set_trace()

    if not nowrite:
        legacyhalos.io.write_sersic(
            galaxy, galaxydir, sersic, modeltype=modeltype, verbose=verbose
        )

    return sersic


def sersic_double(
    galaxy,
    galaxydir,
    ellipsefit,
    minerr=0.01,
    snrmin=1,
    nball=20,
    seed=None,
    debug=False,
    nowavepower=False,
    nowrite=False,
    verbose=False,
):
    """Wrapper to fit a double Sersic model to an input surface brightness profile.

    nowavepower : no wavelength-dependent variation in the Sersic index or
      half-light radius

    """
    if nowavepower:
        modeltype = "double-nowavepower"
        sersic = SersicDoubleWaveFit(
            ellipsefit,
            minerr=minerr,
            snrmin=snrmin,
            nball=nball,
            fix_alpha=True,
            fix_beta=True,
            seed=None,
            modeltype=modeltype,
        )
    else:
        modeltype = "double"
        sersic = SersicDoubleWaveFit(
            ellipsefit,
            minerr=minerr,
            snrmin=snrmin,
            nball=nball,
            fix_alpha=False,
            fix_beta=False,
            seed=None,
            modeltype=modeltype,
        )

    sersic = sersic.fit(verbose=verbose)

    if debug:
        display_sersic(sersic)

    if not nowrite:
        legacyhalos.io.write_sersic(
            galaxy, galaxydir, sersic, modeltype=modeltype, verbose=verbose
        )

    return sersic


def sersic_triple(
    galaxy,
    galaxydir,
    ellipsefit,
    minerr=0.01,
    snrmin=1,
    nball=20,
    seed=None,
    debug=False,
    nowavepower=False,
    nowrite=False,
    verbose=False,
):
    """Wrapper to fit a triple Sersic model to an input surface brightness profile.

    nowavepower : no wavelength-dependent variation in the Sersic index or
      half-light radius

    """
    if nowavepower:
        modeltype = "triple-nowavepower"
        sersic = SersicTripleWaveFit(
            ellipsefit,
            minerr=minerr,
            snrmin=snrmin,
            nball=nball,
            fix_alpha=True,
            fix_beta=True,
            seed=None,
            modeltype=modeltype,
        )
    else:
        modeltype = "triple"
        sersic = SersicTripleWaveFit(
            ellipsefit,
            minerr=minerr,
            snrmin=snrmin,
            nball=nball,
            fix_alpha=False,
            fix_beta=False,
            seed=None,
            modeltype=modeltype,
        )

    sersic = sersic.fit(verbose=verbose)

    if debug:
        display_sersic(sersic, png="junk.png")
    pdb.set_trace()

    if not nowrite:
        legacyhalos.io.write_sersic(
            galaxy, galaxydir, sersic, modeltype=modeltype, verbose=verbose
        )

    return sersic


def legacyhalos_sersic(
    onegal,
    galaxy=None,
    galaxydir=None,
    snrmin=1,
    nball=20,
    minerr=0.1,
    seed=None,
    verbose=False,
    debug=False,
    hsc=False,
):
    """Top-level wrapper script to model the measured surface-brightness profiles
    with various Sersic models.

    """
    if galaxydir is None or galaxy is None:
        if hsc:
            galaxy, galaxydir = legacyhalos.hsc.get_galaxy_galaxydir(onegal)
        else:
            galaxy, galaxydir = legacyhalos.io.get_galaxy_galaxydir(onegal)

    # Read the ellipse-fitting results and
    ellipsefit = legacyhalos.io.read_ellipsefit(galaxy, galaxydir)
    if bool(ellipsefit):
        if ellipsefit["success"]:
            # triple Sersic fit with and without wavelength dependence
            triple_nowave = sersic_triple(
                galaxy,
                galaxydir,
                ellipsefit,
                minerr=minerr,
                snrmin=snrmin,
                nball=nball,
                debug=debug,
                verbose=verbose,
                nowavepower=True,
                seed=seed,
            )

            triple = sersic_triple(
                galaxy,
                galaxydir,
                ellipsefit,
                minerr=minerr,
                snrmin=snrmin,
                nball=nball,
                debug=debug,
                verbose=verbose,
                seed=seed,
            )

            pdb.set_trace()

            # Sersic-exponential fit with and without wavelength dependence
            serexp_nowave = sersic_exponential(
                galaxy,
                galaxydir,
                ellipsefit,
                minerr=minerr,
                snrmin=snrmin,
                nball=nball,
                debug=debug,
                verbose=verbose,
                nowavepower=True,
                seed=seed,
            )

            serexp = sersic_exponential(
                galaxy,
                galaxydir,
                ellipsefit,
                minerr=minerr,
                snrmin=snrmin,
                nball=nball,
                debug=debug,
                verbose=verbose,
                seed=seed,
            )

            # single Sersic fit with and without wavelength dependence
            single_nowave = sersic_single(
                galaxy,
                galaxydir,
                ellipsefit,
                minerr=minerr,
                snrmin=snrmin,
                nball=nball,
                debug=debug,
                verbose=verbose,
                nowavepower=True,
                seed=seed,
            )

            single = sersic_single(
                galaxy,
                galaxydir,
                ellipsefit,
                minerr=minerr,
                snrmin=snrmin,
                nball=nball,
                debug=debug,
                verbose=verbose,
                seed=seed,
            )

            # double Sersic fit with and without wavelength dependence
            double_nowave = sersic_double(
                galaxy,
                galaxydir,
                ellipsefit,
                minerr=minerr,
                snrmin=snrmin,
                nball=nball,
                debug=debug,
                verbose=verbose,
                nowavepower=True,
                seed=seed,
            )

            double = sersic_double(
                galaxy,
                galaxydir,
                ellipsefit,
                minerr=minerr,
                snrmin=snrmin,
                nball=nball,
                debug=debug,
                verbose=verbose,
                seed=seed,
            )

            if single["success"]:
                return 1
            else:
                return 0
        else:
            return 0
    else:
        return 0
