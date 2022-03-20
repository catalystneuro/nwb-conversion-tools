"""Authors: Cody Baker and Ben Dichter."""
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

import spikeextractors as se
import spikeinterface.extractors as si
from pynwb.ecephys import ElectricalSeries

from ..baselfpextractorinterface import BaseLFPExtractorInterface
from ..baserecordingextractorinterface import BaseRecordingExtractorInterface
from ....utils.json_schema import (
    get_schema_from_method_signature,
    get_schema_from_hdmf_class,
    FilePathType,
    dict_deep_update,
)
from ....tools.spikeinterface.spikeinterface import set_recording_channel_property


RECORDING_TYPE = Union[si.SpikeGLXRecordingExtractor, se.SpikeGLXRecordingExtractor]


def fetch_spikeglx_metadata(source_path: FilePathType, recording: RECORDING_TYPE, metadata: dict):
    source_path = Path(source_path)
    if source_path.is_file():
        session_id = source_path.parent.stem
    else:
        session_id = source_path.stem
    if isinstance(recording, se.SpikeGLXRecordingExtractor) and isinstance(recording, se.SubRecordingExtractor):
        current_recording = recording._parent_recording
    else:
        current_recording = recording
    n_shanks = int(current_recording._meta.get("snsShankMap", [1, 1])[1])
    if n_shanks > 1:
        raise NotImplementedError("SpikeGLX metadata for more than a single shank is not yet supported.")
    session_start_time = datetime.fromisoformat(current_recording._meta["fileCreateTime"]).astimezone()

    return dict_deep_update(
        metadata,
        dict(
            NWBFile=dict(
                session_start_time=session_start_time.strftime("%Y-%m-%dT%H:%M:%S"),
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
        ),
    )


def _init_recording(version, file_path, folder_path, **kwargs):
    if version == "v1":
        assert file_path is not None and Path(file_path).is_file(), f"{file_path} should be a file for version='v1'"
        RX = se.SpikeGLXRecordingExtractor
        rx_kwargs = dict(file_path=str(file_path), **kwargs)
        source_data = file_path
    elif version == "v2":
        assert (
            folder_path is not None and Path(folder_path).is_dir()
        ), f"{folder_path} should be a folder for version='v1'"
        RX = si.SpikeGLXRecordingExtractor
        rx_kwargs = dict(folder_path=str(folder_path), **kwargs)
        source_data = folder_path
    else:
        raise ValueError("specify version='v1' for spikeextractors " "version='v2' for spikeinterface")
    return RX, rx_kwargs, source_data


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

    @classmethod
    def get_source_schema(cls):
        return _get_source_schema(cls)

    def __init__(
        self,
        folder_path: FilePathType = None,
        file_path: FilePathType = None,
        recording_version="v2",
        stub_test: Optional[bool] = False,
        **kwargs,
    ):

        self.RX, rx_kwargs, self.source_data = _init_recording_version(
            version=recording_version, file_path=file_path, folder_path=folder_path, **kwargs
        )
        super().__init__(**rx_kwargs)
        if stub_test:
            self.subset_channels = [0, 1]
        # Set electrodes properties
        set_recording_channel_property(
            self.recording_extractor, "shank_electrode_number", self.recording_extractor.get_channel_ids()
        )
        set_recording_channel_property(self.recording_extractor, "shank_group_name", "Shank1")

    def get_metadata_schema(self):
        metadata_schema = super().get_metadata_schema()
        metadata_schema["properties"]["Ecephys"]["properties"].update(
            ElectricalSeries_raw=get_schema_from_hdmf_class(ElectricalSeries)
        )
        return metadata_schema

    def get_metadata(self):
        metadata = super().get_metadata()
        fetch_spikeglx_metadata(folder_path=self.source_path, recording=self.recording_extractor, metadata=metadata)
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
        recording_version="v2",
        stub_test: Optional[bool] = False,
        **kwargs,
    ):
        self.RX, rx_kwargs, self.source_data = _init_recording_version(
            version=recording_version, file_path=file_path, folder_path=folder_path, **kwargs
        )
        super().__init__(**rx_kwargs)
        if stub_test:
            self.subset_channels = [0, 1]
        # Set electrodes properties
        set_recording_channel_property(
            self.recording_extractor, "shank_electrode_number", self.recording_extractor.get_channel_ids()
        )
        set_recording_channel_property(self.recording_extractor, "shank_group_name", "Shank1")

    def get_metadata_schema(self):
        metadata_schema = super().get_metadata_schema()
        metadata_schema["properties"]["Ecephys"]["properties"].update(
            ElectricalSeries_lfp=get_schema_from_hdmf_class(ElectricalSeries)
        )
        return metadata_schema

    def get_metadata(self):
        metadata = super().get_metadata()
        fetch_spikeglx_metadata(folder_path=self.source_data, recording=self.recording_extractor, metadata=metadata)
        metadata["Ecephys"]["ElectricalSeries_lfp"].update(
            description="LFP traces for the processed (lf) SpikeGLX data."
        )
        return metadata

    def get_conversion_options(self):
        conversion_options = dict(stub_test=False)
        return conversion_options
