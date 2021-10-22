"""Authors: Alessio Buccino."""
from spikeextractors import load_extractor_from_pickle

from ..baserecordingextractorinterface import BaseRecordingExtractorInterface
from ..basesortingextractorinterface import BaseSortingExtractorInterface
from ....utils.json_schema import FilePathType


class SIPickleRecordingExtractorInterface(BaseRecordingExtractorInterface):
    """Primary interface for reading and converting SpikeInterface Recording objects through .pkl files."""

    RX = load_extractor_from_pickle

    def __init__(self, file_path: FilePathType):
        super().__init__(pkl_file=file_path)


class SIPickleSortingExtractorInterface(BaseSortingExtractorInterface):
    """Primary interface for reading and converting SpikeInterface Sorting objects through .pkl files."""

    SX = load_extractor_from_pickle

    def __init__(self, file_path: FilePathType):
        super().__init__(pkl_file=file_path)
