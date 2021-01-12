"""Authors: Luiz Tauffer"""
import random
import string
import spikeextractors as se

from ..baserecordingextractorinterface import BaseRecordingExtractorInterface
from ..json_schema_utils import get_schema_from_method_signature
from .interface_utils.brpylib import NsxFile


class BlackrockRecordingInterface(BaseRecordingExtractorInterface):
    """Primary data interface class for converting a BlackrockRecordingExtractor."""

    RX = se.BlackrockRecordingExtractor

    @classmethod
    def get_source_schema(cls):
        """Compile input schema for the RecordingExtractor."""
        return get_schema_from_method_signature(
            class_method=cls.RX.__init__,
            exclude=['block_index', 'seg_index_index']
        )

    def get_metadata(self):
        """Auto-fill as much of the metadata as possible. Must comply with metadata schema."""
        metadata = super().get_metadata()

        # Open file and extract headers
        nsx_file = NsxFile(datafile=self.source_data['filename'])
        session_start_time = nsx_file.basic_header['TimeOrigin']
        comment = nsx_file.basic_header['Comment']

        metadata['NWBFile'] = dict(
            session_start_time=session_start_time,
            session_description=comment,
            identifier=''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
        )

        return metadata