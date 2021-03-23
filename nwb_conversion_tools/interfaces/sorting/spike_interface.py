import spikeextractors as se

from nwb_conversion_tools.interfaces.sorting.base_sorting import BaseSortingExtractorInterface
from nwb_conversion_tools.json_schema_utils import get_base_schema


class SIPickleSortingExtractorInterface(BaseSortingExtractorInterface):
    """Primary interface for reading and converting SpikeInterface objects through Pickle files."""

    @classmethod
    def get_source_schema(cls):
        """Return partial json schema for expected input arguments."""
        return get_base_schema(
            required=['pkl_file'],
            properties=dict(
                pkl_file=dict(type='string')
            )
        )

    def __init__(self, **source_data):
        self.source_data = source_data
        self.sorting_extractor = se.load_extractor_from_pickle(**source_data)