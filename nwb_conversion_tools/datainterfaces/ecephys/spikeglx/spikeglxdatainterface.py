"""Authors: Cody Baker, Ben Dichter, Saksham Sharda."""
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from spikeinterface import BaseRecording
from spikeinterface.core.old_api_utils import OldToNewRecording
import spikeextractors as se
from spikeinterface.extractors import SpikeGLXRecordingExtractor as SpikeGLXRecordingExtractorSI
from pynwb.ecephys import ElectricalSeries

from ..baselfpextractorinterface import BaseLFPExtractorInterface
from ..baserecordingextractorinterface import BaseRecordingExtractorInterface
from ....utils.json_schema import (
    get_schema_from_method_signature,
    get_schema_from_hdmf_class,
    FilePathType,
    dict_deep_update,
)


def fetch_spikeglx_metadata(source_path: FilePathType, recording: BaseRecording, metadata: dict):
    session_id = Path(source_path).stem

    metadata_update = dict(
        NWBFile=dict(
            session_id=session_id,
        ),
        Ecephys=dict(
            Electrodes=[
                dict(name="shank_electrode_number", description="0-indexed channel within a shank."),
                dict(
                    name="shank_group_name",
                    description="The name of the ElectrodeGroup this electrode is a part of.",
                ),
            ]
        ),
    )

    if isinstance(recording, se.SubRecordingExtractor):
        current_recording = recording._parent_recording
    else:
        current_recording = recording
    n_shanks = int(current_recording._meta.get("snsShankMap", [1, 1])[1])
    if n_shanks > 1:
        raise NotImplementedError("SpikeGLX metadata for more than a single shank is not yet supported.")
    session_start_time = datetime.fromisoformat(current_recording._meta["fileCreateTime"]).astimezone()
    metadata_update["NWBFile"]["session_start_time"] = str(session_start_time)

    return dict_deep_update(metadata, metadata_update)


def _get_source_schema(cls):
    source_schema = get_schema_from_method_signature(
        class_method=cls.__init__, exclude=["x_pitch", "y_pitch", "stream_id"]
    )
    source_schema["properties"]["folder_path"]["description"] = (
        "Path to folder containing SpikeGLX files " "(using spikeinterface)."
    )
    source_schema["properties"]["file_path"]["description"] = "Path to SpikeGLX file (using spikeextractors)."
    return source_schema


class SpikeGLXRecordingInterface(BaseRecordingExtractorInterface):
    """Primary data interface class for converting the high-pass (ap) SpikeGLX format."""

    RX = SpikeGLXRecordingExtractorSI

    @classmethod
    def get_source_schema(cls):
        return _get_source_schema(cls)

    def __init__(
        self,
        folder_path: FilePathType = None,
        file_path: FilePathType = None,
        spikeextractors_backend: Optional[bool] = False,
        stub_test: Optional[bool] = False,
        **kwargs,
    ):
        """
        Load and prepare raw acquisition data and corresponding metadata from the Neuropixels format.

        Parameters
        ----------
        folder_path: PathType
            folder containing pair of .ap/.meta or .lf/.meta file
        file_path: PathType
            path to .ap/.lf file if using spikeextractors_backend
        spikeextractors_backend : Optional[bool], optional
            False by default. When True the interface uses the old extractor from the spikextractors library instead
            of a new spikeinterface object.
        stub_test: bool
        kwargs
            additional args depending on usage of spikeextractors or spikeinterface
        """
        if spikeextractors_backend:
            assert (
                file_path is not None and Path(file_path).is_file()
            ), f"{file_path} should be a file if using spikeextractors_backend"
            self.RX = se.SpikeGLXRecordingExtractor
            super().__init__(file_path=str(file_path), **kwargs)
            self.recording_extractor = OldToNewRecording(oldapi_recording_extractor=self.recording_extractor)
            self.folder_path = file_path.parent
        else:
            assert (
                folder_path is not None and Path(folder_path).is_dir()
            ), f"{folder_path} should be a folder for using spikeinterface for extraction"
            super().__init__(folder_path=str(folder_path), **kwargs)
            self.folder_path = folder_path

        if stub_test:
            self.subset_channels = [0, 1]
        # Set electrodes properties
        for chan_id in self.recording_extractor.get_channel_ids():
            self.recording_extractor.set_property("shank_electrode_number", [chan_id], ids=[chan_id])
            self.recording_extractor.set_property("shank_group_name", ["Shank1"], ids=[chan_id])

    def get_metadata_schema(self):
        metadata_schema = super().get_metadata_schema()
        metadata_schema["properties"]["Ecephys"]["properties"].update(
            ElectricalSeries_raw=get_schema_from_hdmf_class(ElectricalSeries)
        )
        return metadata_schema

    def get_metadata(self):
        metadata = super().get_metadata()
        fetch_spikeglx_metadata(source_path=self.folder_path, recording=self.recording_extractor, metadata=metadata)
        metadata["Ecephys"]["ElectricalSeries_raw"] = dict(
            name="ElectricalSeries_raw", description="Raw acquisition traces for the high-pass (ap) SpikeGLX data."
        )
        return metadata

    def get_conversion_options(self):
        conversion_options = dict(write_as="raw", es_key="ElectricalSeries_raw", stub_test=False)
        return conversion_options


class SpikeGLXLFPInterface(BaseLFPExtractorInterface):
    """Primary data interface class for converting the low-pass (ap) SpikeGLX format."""

    @classmethod
    def get_source_schema(cls):
        return _get_source_schema(cls)

    def __init__(
        self,
        folder_path: FilePathType = None,
        file_path: FilePathType = None,
        spikeextractors_backend: Optional[bool] = False,
        stub_test: Optional[bool] = False,
        **kwargs,
    ):
        if spikeextractors_backend:
            assert file_path is not None and Path(file_path).is_file(), f"{file_path} should be a file for version='v1'"
            self.RX = se.SpikeGLXRecordingExtractor
            super().__init__(file_path=str(file_path), **kwargs)
            self.recording_extractor = OldToNewRecording(oldapi_recording_extractor=self.recording_extractor)
            self.folder_path = file_path.parent
        else:
            assert (
                folder_path is not None and Path(folder_path).is_dir()
            ), f"{folder_path} should be a folder for version='v2'"
            super().__init__(folder_path=str(folder_path), **kwargs)
            self.folder_path = folder_path

        if stub_test:
            self.subset_channels = [0, 1]
        # Set electrodes properties
        for chan_id in self.recording_extractor.get_channel_ids():
            self.recording_extractor.set_property("shank_electrode_number", [chan_id], ids=[chan_id])
            self.recording_extractor.set_property("shank_group_name", ["Shank1"], ids=[chan_id])

    def get_metadata_schema(self):
        metadata_schema = super().get_metadata_schema()
        metadata_schema["properties"]["Ecephys"]["properties"].update(
            ElectricalSeries_lfp=get_schema_from_hdmf_class(ElectricalSeries)
        )
        return metadata_schema

    def get_metadata(self):
        metadata = super().get_metadata()
        fetch_spikeglx_metadata(
            source_path=self.sglx_source_path, recording=self.recording_extractor, metadata=metadata
        )
        metadata["Ecephys"]["ElectricalSeries_lfp"].update(
            description="LFP traces for the processed (lf) SpikeGLX data."
        )
        return metadata

    def get_conversion_options(self):
        conversion_options = dict(stub_test=False)
        return conversion_options
