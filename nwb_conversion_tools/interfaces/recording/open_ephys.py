"""Authors: Luiz Tauffer"""
import pytz
import uuid
from typing import Union, Optional
from pathlib import Path
import spikeextractors as se

from nwb_conversion_tools.interfaces.recording.base_recording import BaseRecordingExtractorInterface
from nwb_conversion_tools.json_schema_utils import get_schema_from_method_signature

PathType = Union[str, Path, None]


class OpenEphysRecordingExtractorInterface(BaseRecordingExtractorInterface):
    """Primary data interface class for converting a OpenEphysRecordingExtractor."""

    RX = se.OpenEphysRecordingExtractor

    @classmethod
    def get_source_schema(cls):
        """Compile input schema for the RecordingExtractor."""
        metadata_schema = get_schema_from_method_signature(
            class_method=cls.__init__,
            exclude=['recording_id', 'experiment_id', 'stub_test']
        )
        metadata_schema['properties']['folder_path']['format'] = 'directory'
        metadata_schema['properties']['folder_path']['description'] = 'Path to directory containing OpenEphys files.'
        metadata_schema['additionalProperties'] = True
        return metadata_schema
    
    def __init__(self, folder_path: PathType, experiment_id: Optional[int] = 0, 
                 recording_id: Optional[int] = 0, stub_test: Optional[bool] = False):
        super().__init__(folder_path=str(folder_path), experiment_id=experiment_id, 
                         recording_id=recording_id)
        if stub_test:
            self.subset_channels = [0, 1]

    def get_metadata(self):
        """Auto-fill as much of the metadata as possible. Must comply with metadata schema."""
        metadata = super().get_metadata()

        # Open file and extract info
        session_start_time = self.recording_extractor._fileobj.experiments[0].datetime
        session_start_time_tzaware = pytz.timezone('EST').localize(session_start_time)

        metadata['NWBFile'] = dict(
            session_start_time=session_start_time_tzaware,
            identifier=str(uuid.uuid1())
        )

        # Ecephys metadata
        device_name = self.recording_extractor._fileobj.experiments[0].acquisition_system
        metadata['Ecephys'] = dict(
            Device=[dict(
                name=device_name,
                description='no description'
            )],
            ElectrodeGroup=[],
        )

        return metadata


