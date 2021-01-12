"""Authors: Luiz Tauffer"""
import spikeextractors as se

from ..baserecordingextractorinterface import BaseRecordingExtractorInterface
from ..json_schema_utils import get_schema_from_method_signature


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
    
        return metadata