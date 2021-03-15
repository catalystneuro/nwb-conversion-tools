"""Authors: Cody Baker and Ben Dichter."""
from spikeextractors import NeuralynxRecordingExtractor

from ..baserecordingextractorinterface import BaseRecordingExtractorInterface
from ..json_schema_utils import get_schema_from_method_signature


class NeuralynxRecordingInterface(BaseRecordingExtractorInterface):
    """Primary data interface class for converting the Neuralynx format."""

    RX = NeuralynxRecordingExtractor
