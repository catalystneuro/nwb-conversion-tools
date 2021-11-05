"""Authors: Alessio Buccino."""
from spikeextractors import load_extractor_from_pickle

from ..baserecordingextractorinterface import BaseRecordingExtractorInterface
from ..basesortingextractorinterface import BaseSortingExtractorInterface
from ....utils.json_schema import FilePathType
from ....utils import map_si_object_to_writer


class SIPickleRecordingExtractorInterface(BaseRecordingExtractorInterface):
    """Primary interface for reading and converting SpikeInterface Recording objects through .pkl files."""

    RX = load_extractor_from_pickle

    def __init__(self, pkl_file: FilePathType):
        super(SIPickleRecordingExtractorInterface, self).__init__(pkl_file=pkl_file)


class SIPickleSortingExtractorInterface(BaseSortingExtractorInterface):
    """Primary interface for reading and converting SpikeInterface Sorting objects through .pkl files."""

    SX = load_extractor_from_pickle

    def __init__(self, pkl_file: FilePathType):
        super(SIPickleSortingExtractorInterface, self).__init__(pkl_file=pkl_file)
