"""Authors: Alessio Buccino."""
import spikeextractors as se

from nwb_conversion_tools.interfaces.recording.base_recording import BaseRecordingExtractorInterface
from nwb_conversion_tools.json_schema_utils import get_base_schema


class SIPickleRecordingExtractorInterface(BaseRecordingExtractorInterface):
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
        self.subset_channels = None
        self.recording_extractor = se.load_extractor_from_pickle(**source_data)


