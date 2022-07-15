"""Authors: Heberto Mayorquin, Cody Baker, Ben Dichter and Julia Sprenger"""
import warnings
from pathlib import Path
from natsort import natsorted
import json

from spikeinterface.extractors import NeuralynxRecordingExtractor
from spikeinterface.core.old_api_utils import OldToNewRecording
from spikeinterface import BaseRecording

import spikeextractors as se

from ..baserecordingextractorinterface import BaseRecordingExtractorInterface
from ....utils import FolderPathType
from ....utils.json_schema import dict_deep_update


def get_common_metadata(extractors: list[NeuralynxRecordingExtractor]) -> dict:
    """
    Parse the header of one of the .ncs files to get the session start time (without
    timezone) and the session_id.
    Parameters
    ----------
    extractors: list of NeuralynxRecordingExtractor objects

    Returns
    -------
    dict
    """

    key_mapping = {
        "recording_opened": "session_start_time",
        "sessionUUID": "session_id",
    }

    # check if neuralynx file header objects are present and use these for consensus extraction
    if hasattr(extractors[0].neo_reader, "file_headers"):
        headers = [list(e.neo_reader.file_headers.values())[0] for e in extractors]
        common_keys = list(set.intersection(*[set(h.keys()) for h in headers]))
        common_header = {k: headers[0][k] for k in common_keys if all([headers[0][k] == h[k] for h in headers])}

    # use minimal set of metadata of first recording
    else:
        neo_annotations = extractors[0].neo_reader.raw_annotations
        signal_info = neo_annotations["blocks"][0]["segments"][0]["signals"][0]
        annotations = signal_info["__array_annotations__"]
        common_header = {k: annotations.get(k, None) for k in key_mapping}

        # # extraction of general metadata and remapping of of keys to nwb terms
        # general_metadata['session_start_time'] = annotations['recording_opened']
        # general_metadata['session_id'] = annotations.get('SessionUUID', '')

    # mapping to nwb terms
    for neuralynx_key, nwb_key in key_mapping.items():
        common_header.setdefault(nwb_key, common_header.pop(neuralynx_key, None))

    # reformat session_start_time
    start_time = common_header["session_start_time"]
    if hasattr(start_time, "__iter__") and len(start_time) == 1:
        common_header["session_start_time"] = common_header["session_start_time"][0]

    # convert version objects back to string
    if common_header.get("ApplicationVersion", None) is not None:
        common_header["ApplicationVersion"] = str(common_header["ApplicationVersion"])

    return common_header


def get_filtering(extractor: NeuralynxRecordingExtractor) -> str:
    """Get the filtering metadata from a .ncs file.
    Parameters
    ----------
    extractor: NeuralynxRecordingExtractor
        NeuralynxRecordingExtractor to be annotated with filter information
        from linked neo.NeuralynxIO

    Returns
    -------
    str: string representation of a dictionary containing the filter settings
    """

    # extracting filter annotations
    neo_annotations = extractor.neo_reader.raw_annotations
    signal_info = neo_annotations["blocks"][0]["segments"][0]["signals"][0]
    signal_annotations = signal_info["__array_annotations__"]
    filter_dict = {k: v for k, v in signal_annotations.items() if k.lower().startswith("dsp")}

    # conversion to string values
    for key, value in filter_dict.items():
        filter_dict[key] = " ".join(value)

    filter_info = json.dumps(filter_dict, ensure_ascii=True)

    return filter_info


class NeuralynxRecordingInterface(BaseRecordingExtractorInterface):
    """Primary data interface class for converting the Neuralynx format."""

    RX = NeuralynxRecordingExtractor

    def __init__(self, folder_path: FolderPathType, spikeextractors_backend: bool = False, verbose: bool = True):

        self.nsc_files = natsorted([str(x) for x in Path(folder_path).iterdir() if ".ncs" in x.suffixes])

        if spikeextractors_backend:
            self.initialize_in_spikeextractors(folder_path=folder_path, verbose=verbose)
            self.recording_extractor = OldToNewRecording(oldapi_recording_extractor=self.recording_extractor)
        else:
            super().__init__(folder_path=folder_path, verbose=verbose)
            self.recording_extractor = self.recording_extractor.select_segments(segment_indices=0)

        # General
        self.add_recording_extractor_properties()

    def initialize_in_spikeextractors(self, folder_path, verbose):
        self.RX = se.MultiRecordingChannelExtractor
        self.subset_channels = None
        self.source_data = dict(folder_path=folder_path, verbose=verbose)
        self.verbose = verbose

        ncs_files = natsorted([str(x) for x in Path(folder_path).iterdir() if ".ncs" in x.suffixes])
        extractors = []
        seg_index = 0
        # generate one extractor for each neo file and recording segment combination
        for filename in ncs_files:
            first_extractor = NeuralynxRecordingExtractor(filename=filename, seg_index=seg_index)
            n_segments = first_extractor.neo_reader.segment_count(block_index=0)
            extractors.append(first_extractor)
            for i in range(1, n_segments):
                extractors.append(NeuralynxRecordingExtractor(filename=filename, seg_index=i))
        self.recording_extractor = self.RX(extractors)

        gains = [extractor.get_channel_gains()[0] for extractor in extractors]
        for extractor in extractors:
            extractor.clear_channel_gains()
        self.recording_extractor.set_channel_gains(gains=gains)

        for i, extractor in enumerate(extractors):
            filter_info = get_filtering(extractor)
            self.recording_extractor.set_property(key="filtering", values=filter_info)

    def get_metadata(self):
        # extracting general session metadata exemplary from first recording
        new_metadata = dict(NWBFile=get_common_metadata(self.recording_extractor._recordings))
        return dict_deep_update(super().get_metadata(), new_metadata)
