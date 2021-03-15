"""Authors: Cody Baker and Ben Dichter."""
from spikeextractors import NeuralynxRecordingExtractor

from ..baserecordingextractorinterface import BaseRecordingExtractorInterface
from ..json_schema_utils import get_schema_from_method_signature


class NeuralynxRecordingInterface(BaseRecordingExtractorInterface):
    """Primary data interface class for converting the Neuralynx format."""

    RX = NeuralynxRecordingExtractor

    @classmethod
    def get_source_schema(cls):
        metadata_schema = get_schema_from_method_signature(
            class_method=cls.RX.__init__,
            exclude=['block_index', 'seg_index']
        )
        metadata_schema['additionalProperties'] = True
        metadata_schema['properties']['dirname']['format'] = 'folder'
        metadata_schema['properties']['dirname']['description'] = 'Path to Neuralynx folder.'
        return metadata_schema
