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
from jsonschema import validate
from ...utils import map_si_object_to_writer
from ...utils.common_writer_tools import default_export_ops, default_export_ops_schema

OptionalPathType = Optional[Union[str, Path]]


class BaseRecordingExtractorInterface(BaseDataInterface, ABC):
    """Primary class for all RecordingExtractorInterfaces."""

    RX = None

    def __init__(self, **source_data):
        super().__init__(**source_data)
        self.recording_extractor = self.RX(**source_data)
        self.writer_class = map_si_object_to_writer(self.recording_extractor)(self.recording_extractor)
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
                required=["name", "description"],
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
                for group_id in np.unique(self.writer_class._get_channel_property_values("group"))
            ],
        )
        return metadata

    def subset_recording(self):
        """
        Subset a recording extractor according to stub and channel subset options.

        Parameters
        ----------
        stub_test : bool, optional (default False)
        """
        self.writer_class = map_si_object_to_writer(self.recording_extractor)(
            self.recording_extractor,
            stub=True,
        )

    def run_conversion(
        self,
        nwbfile: NWBFile,
        metadata: dict = None,
        stub_test: bool = False,
        save_path: OptionalPathType = None,
        overwrite: bool = False,
        **kwargs,
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
        buffer_gb: float (optional, defaults to 1.0GB)
            Maximum amount of memory (in GB) to use per iteration of the internal DataChunkIterator.
        write_as: str (optional, defaults to 'raw')
            Options: 'raw', 'lfp' or 'processed'
        es_key: str (optional)
            Key in metadata dictionary containing metadata info for the specific electrical series
        """
        if stub_test:
            self.subset_recording()

        conversion_opts = default_export_ops()
        conversion_opts.update(**kwargs)
        conversion_opt_schema = default_export_ops_schema()
        validate(instance=conversion_opts, schema=conversion_opt_schema)

        self.writer_class.add_to_nwb(nwbfile, metadata, **conversion_opts)
        if save_path is not None:
            if overwrite:
                if Path(save_path).exists():
                    Path(save_path).unlink()
                with NWBHDF5IO(str(save_path), mode="w") as io:
                    io.write(self.writer_class.nwbfile)
