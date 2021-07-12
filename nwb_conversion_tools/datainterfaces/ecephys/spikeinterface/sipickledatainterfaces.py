"""Authors: Alessio Buccino."""
import spikeextractors as se

from ..baserecordingextractorinterface import BaseRecordingExtractorInterface
from ..basesortingextractorinterface import BaseSortingExtractorInterface
from ....utils.json_schema import get_schema_from_method_signature


class SIPickleRecordingExtractorInterface(BaseRecordingExtractorInterface):
    """Primary interface for reading and converting SpikeInterface objects through Pickle files."""

    @classmethod
    def get_source_schema(cls):
        return get_schema_from_method_signature(cls.__init__)

    def __init__(self, pkl_file: str):
        super().__init__(pkl_file=pkl_file)
        self.subset_channels = None
        self.recording_extractor = se.load_extractor_from_pickle(pkl_file=pkl_file)


class SIPickleSortingExtractorInterface(BaseSortingExtractorInterface):
    """Primary interface for reading and converting SpikeInterface objects through Pickle files."""

    @classmethod
    def get_source_schema(cls):
        return get_schema_from_method_signature(cls.__init__)

    def __init__(self, pkl_file: str):
        super().__init__(pkl_file=pkl_file)
        self.sorting_extractor = se.load_extractor_from_pickle(pkl_file=pkl_file)
