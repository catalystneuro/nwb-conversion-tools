"""Authors: Cody Baker and Ben Dichter."""
from pathlib import Path
from natsort import natsorted
from glob import glob
from dateutil import parser


from spikeextractors import MultiRecordingChannelExtractor, NeuralynxRecordingExtractor

from ..baserecordingextractorinterface import BaseRecordingExtractorInterface
from ....utils import FolderPathType
from ....utils.json_schema import dict_deep_update


def get_metadata(folder_path):
    fpath = glob(folder_path + "/*.ncs")[0]
    with open(fpath, "r", encoding="latin1") as file:
        header = file.read(1024)
    index = header.find("TimeCreated") + 12
    session_start_time = parser.parse(header[index:index+19])

    index = header.find("SessionUUID") + 12
    session_id = header[index:index + 36]

    return dict(
        session_start_time=session_start_time,
        session_id=session_id,
    )


class NeuralynxRecordingInterface(BaseRecordingExtractorInterface):
    """Primary data interface class for converting the Neuralynx format."""

    RX = MultiRecordingChannelExtractor

    def __init__(self, folder_path: FolderPathType):
        self.subset_channels = None
        self.source_data = dict(folder_path=folder_path)
        neuralynx_files = natsorted([str(x) for x in Path(folder_path).iterdir() if ".ncs" in x.suffixes])
        extractors = [NeuralynxRecordingExtractor(filename=filename, seg_index=0) for filename in neuralynx_files]
        gains = [extractor.get_channel_gains()[0] for extractor in extractors]
        for extractor in extractors:
            extractor.clear_channel_gains()
        self.recording_extractor = self.RX(extractors)
        self.recording_extractor.set_channel_gains(gains=gains)

    def get_metadata(self):
        return dict_deep_update(
            super().get_metadata(),
            dict(NWBFile=get_metadata(self.source_data["folder_path"]))
        )

