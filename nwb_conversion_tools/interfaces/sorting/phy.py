"""Authors: Cody Baker."""
import spikeextractors as se

from nwb_conversion_tools.interfaces.sorting.base_sorting import BaseSortingExtractorInterface


class PhySortingInterface(BaseSortingExtractorInterface):
    """Primary data interface class for converting a PhySortingExtractor."""

    SX = se.PhySortingExtractor
