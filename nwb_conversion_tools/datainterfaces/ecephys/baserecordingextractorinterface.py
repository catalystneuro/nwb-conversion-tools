"""Authors: Cody Baker, Ben Dichter, Saksham Sharda."""
from abc import ABC
from typing import Union, Optional
from pathlib import Path
import numpy as np

from pynwb import NWBFile, NWBHDF5IO
from pynwb.device import Device
from pynwb.ecephys import ElectrodeGroup

from ...basedatainterface import BaseDataInterface
from ...utils.json_schema import (
    get_schema_from_hdmf_class,
    get_schema_from_method_signature,
    get_base_schema,
)
from ...utils import map_si_object_to_writer

OptionalPathType = Optional[Union[str, Path]]


class BaseRecordingExtractorInterface(BaseDataInterface, ABC):
    """Primary class for all RecordingExtractorInterfaces."""

    RX = None

    @classmethod
    def get_source_schema(cls):
        """Compile input schema for the RecordingExtractor."""
        return get_schema_from_method_signature(cls.RX.__init__)

    def __init__(self, **source_data):
        super().__init__(**source_data)
        self.recording_extractor = self.RX(**source_data)
        self.writer_class = map_si_object_to_writer(self.recording_extractor)(self.recording_extractor)
        self.subset_channels = None
        self.source_data = source_data

    def get_metadata_schema(self):
        """Compile metadata schema for the RecordingExtractor."""
        metadata_schema = super().get_metadata_schema()

        # Initiate Ecephys metadata
        metadata_schema["properties"]["Ecephys"] = get_base_schema(tag="Ecephys")
        metadata_schema["properties"]["Ecephys"]["required"] = ["Device", "ElectrodeGroup"]
        metadata_schema["properties"]["Ecephys"]["properties"] = dict(
            Device=dict(type="array", minItems=1, items={"$ref": "#/properties/Ecephys/properties/definitions/Device"}),
            ElectrodeGroup=dict(
                type="array", minItems=1, items={"$ref": "#/properties/Ecephys/properties/definitions/ElectrodeGroup"}
            ),
            Electrodes=dict(
                type="array",
                minItems=0,
                renderForm=False,
                items={"$ref": "#/properties/Ecephys/properties/definitions/Electrodes"},
            ),
        )
        # Schema definition for arrays
        metadata_schema["properties"]["Ecephys"]["properties"]["definitions"] = dict(
            Device=get_schema_from_hdmf_class(Device),
            ElectrodeGroup=get_schema_from_hdmf_class(ElectrodeGroup),
            Electrodes=dict(
                type="object",
                additionalProperties=False,
                required=["name"],
                properties=dict(
                    name=dict(type="string", description="name of this electrodes column"),
                    description=dict(type="string", description="description of this electrodes column"),
                ),
            ),
        )
        return metadata_schema

    def get_metadata(self):
        metadata = super().get_metadata()
        metadata["Ecephys"] = dict(
            Device=[dict(name="Device_ecephys", description="no description")],
            ElectrodeGroup=[
                dict(name=str(group_id), description="no description", location="unknown", device="Device_ecephys")
                for group_id in np.unique(self.writer_class._get_channel_property_values('group'))
            ],
        )
        return metadata

    def subset_recording(self, nwbfile, metadata, **kwargs):
        """
        Subset a recording extractor according to stub and channel subset options.

        Parameters
        ----------
        stub_test : bool, optional (default False)
        """
        self.writer_class = map_si_object_to_writer(self.recording_extractor)(self.recording_extractor,
                                                                              nwbfile=nwbfile,
                                                                              metadata=metadata,
                                                                              stub=True,
                                                                              stub_channels=self.subset_channels,
                                                                              **kwargs)

    def run_conversion(
        self,
        nwbfile: NWBFile,
        metadata: dict = None,
        stub_test: bool = False,
        use_times: bool = False,
        save_path: OptionalPathType = None,
        overwrite: bool = False,
        buffer_mb: int = 500,
        write_as: str = "raw",
        es_key: str = None,
    ):
        """
        Primary function for converting raw (unprocessed) RecordingExtractor data to the NWB standard.

        Parameters
        ----------
        nwbfile: NWBFile
            nwb file to which the recording information is to be added
        metadata: dict
            metadata info for constructing the nwb file (optional).
            Should be of the format
                metadata['Ecephys']['ElectricalSeries'] = dict(name=my_name, description=my_description)
        use_times: bool
            If True, the times are saved to the nwb file using recording.frame_to_time(). If False (default),
            the sampling rate is used.
        save_path: PathType
            Required if an nwbfile is not passed. Must be the path to the nwbfile
            being appended, otherwise one is created and written.
        overwrite: bool
            If using save_path, whether or not to overwrite the NWBFile if it already exists.
        stub_test: bool, optional (default False)
            If True, will truncate the data to run the conversion faster and take up less memory.
        buffer_mb: int (optional, defaults to 500MB)
            Maximum amount of memory (in MB) to use per iteration of the internal DataChunkIterator.
            Requires trace data in the RecordingExtractor to be a memmap object.
        write_as: str (optional, defaults to 'raw')
            Options: 'raw', 'lfp' or 'processed'
        es_key: str (optional)
            Key in metadata dictionary containing metadata info for the specific electrical series
        """
        if stub_test or self.subset_channels is not None:
            self.subset_recording(nwbfile,
                                  metadata,
                                  use_times=use_times,
                                  buffer_mb=buffer_mb,
                                  write_as=write_as,
                                  es_key=es_key,
            )

        self.writer_class.write_to_nwb()
        if save_path is not None:
            if overwrite:
                if Path(save_path).exists():
                    Path(save_path).unlink()
                with NWBHDF5IO(str(save_path), mode="w") as io:
                    io.write(self.writer_class.nwbfile)
