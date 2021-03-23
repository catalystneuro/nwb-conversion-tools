"""
"""
from roiextractors import SbxImagingExtractor, Hdf5ImagingExtractor, \
    TiffImagingExtractor
from nwb_conversion_tools.interfaces.imaging.base_imaging import BaseImagingExtractorInterface


class TiffImagingInterface(BaseImagingExtractorInterface):
    """
    Data Interface for TIffImagingExtractor
    """

    IX = TiffImagingExtractor


class Hdf5ImagingInterface(BaseImagingExtractorInterface):
    """
    Data Interface for Hdf5ImagingExtractor
    """

    IX = Hdf5ImagingExtractor


class SbxImagingInterface(BaseImagingExtractorInterface):
    """
    Data Interface for SbxImagingExtractor
    """

    IX = SbxImagingExtractor
