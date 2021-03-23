from typing import Optional

import spikeextractors as se

from nwb_conversion_tools.interfaces.recording.blackrock import PathType
from nwb_conversion_tools.interfaces.sorting.base_sorting import BaseSortingExtractorInterface
from nwb_conversion_tools.json_schema_utils import get_schema_from_method_signature


class BlackrockSortingExtractorInterface(BaseSortingExtractorInterface):
    """Primary data interface class for converting Blackrock spiking data."""

    SX = se.BlackrockSortingExtractor

    @classmethod
    def get_source_schema(cls):
        """Compile input schema for the RecordingExtractor."""
        metadata_schema = get_schema_from_method_signature(
            class_method=cls.SX.__init__,
            exclude=['block_index', 'seg_index', 'nsx_to_load']
        )
        metadata_schema['additionalProperties'] = True
        metadata_schema['properties']['filename']['format'] = 'file'
        metadata_schema['properties']['filename']['description'] = 'Path to Blackrock file.'
        return metadata_schema

    def __init__(self, filename: PathType, nsx_to_load: Optional[int] = None):
        super().__init__(filename=filename, nsx_to_load=nsx_to_load)