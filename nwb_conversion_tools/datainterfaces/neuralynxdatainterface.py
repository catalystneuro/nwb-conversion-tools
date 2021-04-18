"""Authors: Cody Baker."""
from pathlib import Path
from re import search
import numpy as np

from spikeextractors import MultiRecordingChannelExtractor, NeuralynxRecordingExtractor

from ..baserecordingextractorinterface import BaseRecordingExtractorInterface


class NeuralynxRecordingInterface(BaseRecordingExtractorInterface):
    """Primary data interface class for converting the Neuralynx format."""

    RX = MultiRecordingChannelExtractor

    @classmethod
    def get_source_schema(cls):
        return dict(
            required=["dirname"],
            properties=dict(
                dirname=dict(
                    type="string",
                    format="folder",
                    description="Path to Neuralynx folder."
                ),
            ),
            type="object",
            additionalProperties=True
        )

    # The Neuralynx IO requires a slight workaround due to the folder based functionality of the neo IO being
    # buggy with all the different versions of Neuralynx available. The safest method is to construct a
    # MultiChannelRecordingExtractor containing individually loaded NeuralynxRecordingExtractors via filenames
    def __init__(self, **source_data):
        self.source_data = source_data
        neuralynx_files = [x for x in Path(self.source_data["dirname"]).iterdir() if ".ncs" in x.suffixes]
        file_nums = [int(search(r"\d+$", filename.stem)[0]) for filename in neuralynx_files]
        sort_idx = np.argsort(file_nums)
        sorted_neuralynx_files = (np.array(neuralynx_files)[sort_idx]).tolist()
        self.recording_extractor = self.RX(
            [NeuralynxRecordingExtractor(filename=filename) for filename in sorted_neuralynx_files]
        )
        self.subset_channels = None
