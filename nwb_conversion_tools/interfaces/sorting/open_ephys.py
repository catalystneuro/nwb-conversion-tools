from typing import Optional

import spikeextractors as se

from nwb_conversion_tools.interfaces.recording.open_ephys import PathType
from nwb_conversion_tools.interfaces.sorting.base_sorting import BaseSortingExtractorInterface
from nwb_conversion_tools.json_schema_utils import get_schema_from_method_signature


class OpenEphysSortingExtractorInterface(BaseSortingExtractorInterface):
    """Primary data interface class for converting OpenEphys spiking data."""

    SX = se.OpenEphysSortingExtractor

    @classmethod
    def get_source_schema(cls):
        """Compile input schema for the SortingExtractor."""
        metadata_schema = get_schema_from_method_signature(
            class_method=cls.__init__,
            exclude=['recording_id', 'experiment_id']
        )
        metadata_schema['properties']['folder_path']['format'] = 'directory'
        metadata_schema['properties']['folder_path']['description'] = 'Path to directory containing OpenEphys files.'
        metadata_schema['additionalProperties'] = False
        return metadata_schema

    def __init__(self, folder_path: PathType, experiment_id: Optional[int] = 0,
                 recording_id: Optional[int] = 0):
        super().__init__(folder_path=str(folder_path), experiment_id=experiment_id,
                         recording_id=recording_id)