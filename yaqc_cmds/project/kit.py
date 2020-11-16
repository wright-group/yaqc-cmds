"""
a collection of small, general purpose objects and methods
"""


### import ####################################################################


import numpy as np


### math ######################################################################


def grating_linear_dispersion(
    spec_inclusion_angle,
    spec_focal_length,
    spec_focal_length_tilt,
    spec_grooves_per_mm,
    spec_central_wavelength,
    spec_order,
    number_of_pixels,
    pixel_width,
    calibration_pixel,
):
    """
    Parameters
    ----------
    spec_inclusion_angle : float
        Spectrometer inclusion angle (degrees).
    spec_focal_length : float
        Spectrometer focal length (mm).
    spec_focal_length_tilt : float
        Spectrometer focal length tilt (degrees).
    spec_grooves_per_mm : float
        Spectrometer grating grooves per mm.
    spec_central_wavelength : float
        Spectrometer set wavelength (nm).
    spec_order : int
        Spectrometer order of diffraction.
    number_of_pixels : int
        Number of pixels on array detector.
    pixel_width : float
        Pixel width (um)
    calibration_pixel : int
        Pixel on which the spec_central_wavelength falls.

    Returns
    -------
    np.ndarray
        Color found on each pixel (nm)
    """
    # translate inputs into appropriate internal units
    spec_inclusion_angle_rad = np.radians(spec_inclusion_angle)
    spec_focal_length_tilt_rad = np.radians(spec_focal_length_tilt)
    pixel_width_mm = pixel_width / 1e3
    # create array
    i_pixel = np.arange(number_of_pixels)
    # calculate terms
    x = np.arcsin(
        (1e-6 * spec_order * spec_grooves_per_mm * spec_central_wavelength)
        / (2 * np.cos(spec_inclusion_angle_rad / 2.0))
    )
    A = np.sin(x - spec_inclusion_angle_rad / 2)
    B = np.sin(
        (spec_inclusion_angle_rad)
        + x
        - (spec_inclusion_angle_rad / 2)
        - np.arctan(
            (
                pixel_width_mm * (i_pixel - calibration_pixel)
                + spec_focal_length * spec_focal_length_tilt_rad
            )
            / (spec_focal_length * np.cos(spec_focal_length_tilt_rad))
        )
    )
    out = ((A + B) * 1e6) / (spec_order * spec_grooves_per_mm)
    return out


### testing ###################################################################

if __name__ == "__main__":
    arr = grating_linear_dispersion(
        spec_inclusion_angle=24.0,
        spec_focal_length=140.0,
        spec_focal_length_tilt=0.0,
        spec_grooves_per_mm=300.0,
        spec_central_wavelength=1300.0,
        spec_order=1,
        number_of_pixels=256,
        pixel_width=50.0,
        calibration_pixel=100,
    )
    print(arr[100])
