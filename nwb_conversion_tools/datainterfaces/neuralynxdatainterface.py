"""Authors: Cody Baker and Ben Dichter."""
from spikeextractors import NeuralynxRecordingExtractor

from ..baserecordingextractorinterface import BaseRecordingExtractorInterface


class NeuralynxRecordingInterface(BaseRecordingExtractorInterface):
    """Primary data interface class for converting the Neuralynx format."""

    RX = NeuralynxRecordingExtractor
