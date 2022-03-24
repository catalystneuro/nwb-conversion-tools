"""Authors: Cody Baker and Ben Dichter."""
import warnings
from pathlib import Path
from natsort import natsorted
from glob import glob
from dateutil import parser


from spikeextractors import MultiRecordingChannelExtractor, NeuralynxRecordingExtractor

from ..baserecordingextractorinterface import BaseRecordingExtractorInterface
from ....utils import FolderPathType
from ....utils.json_schema import dict_deep_update


def get_metadata(folder_path):
    """
    Parse the header of one of the .ncs files to get the session start time (without
    timezone) and the session_id.

    Parameters
    ----------
    folder_path: str

    Returns
    -------
    dict

    """
    fpath = glob(folder_path + "/*.ncs")[0]
    with open(fpath, "r", encoding="latin1") as file:
        header = file.read(1024)
    index = header.find("TimeCreated") + 12
    session_start_time = parser.parse(header[index : index + 19])

    index = header.find("SessionUUID") + 12
    session_id = header[index : index + 36]

    return dict(
        session_start_time=session_start_time,
        session_id=session_id,
        identifier=session_id,
    )

def get_filtering(channel_path):
    """Get the filtering metadata from an .nsc file.

    Parameters
    ----------
    channel_path: str
        Filepath for an .nsc file

    Returns
    -------
    str:
        json dump of filter parameters. Uses the mu character, which may cause problems
        for downstream things that expect ASCII.
    """

    with open(channel_path, "r", encoding="latin1") as file:
        header = file.read(1024)
    out = {}
    for line in text.split("\n\n")[-1].split("\n"):
        if line[0] == '-':
            key, val = line.split(' ')
            out[key[1:]] = val

    return json.dumps(out, ensure_ascii=False)


class NeuralynxRecordingInterface(BaseRecordingExtractorInterface):
    """Primary data interface class for converting the Neuralynx format."""

    RX = MultiRecordingChannelExtractor

    def __init__(self, folder_path: FolderPathType):
        self.subset_channels = None
        self.source_data = dict(folder_path=folder_path)
        nsc_files = natsorted([str(x) for x in Path(folder_path).iterdir() if ".ncs" in x.suffixes])
        extractors = [NeuralynxRecordingExtractor(filename=filename, seg_index=0) for filename in nsc_files]
        gains = [extractor.get_channel_gains()[0] for extractor in extractors]
        for extractor in extractors:
            extractor.clear_channel_gains()
        self.recording_extractor = self.RX(extractors)
        self.recording_extractor.set_channel_gains(gains=gains)
        try:
            for i, filename in enumerate(nsc_files):
                self.recording_extractor.set_channel_property(
                    i,
                    "filtering",
                    get_filtering(filename),
                )
        except:
            warnings.warn("filtering could not be extracted.")

    def get_metadata(self):
        return dict_deep_update(super().get_metadata(), dict(NWBFile=get_metadata(self.source_data["folder_path"])))
