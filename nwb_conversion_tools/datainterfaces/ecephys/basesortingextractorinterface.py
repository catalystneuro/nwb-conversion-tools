"""Authors: Cody Baker and Ben Dichter."""
from abc import ABC
from pathlib import Path
import spikeextractors as se
import numpy as np
from pynwb import NWBFile, NWBHDF5IO
from pynwb.ecephys import SpikeEventSeries
from jsonschema import validate
from ...basedatainterface import BaseDataInterface
from ...utils.json_schema import (
    get_schema_from_hdmf_class,
    get_base_schema,
    get_schema_from_method_signature,
    fill_defaults,
)
from ...utils.common_writer_tools import default_export_ops, default_export_ops_schema
from ...utils import export_ecephys_to_nwb
from .baserecordingextractorinterface import BaseRecordingExtractorInterface, map_si_object_to_writer, OptionalPathType


class BaseSortingExtractorInterface(BaseDataInterface, ABC):
    """Primary class for all SortingExtractor intefaces."""

    SX = None

    @classmethod
    def get_source_schema(cls):
        """Compile input schema for the SortingExtractor."""
        return get_schema_from_method_signature(cls.__init__)

    def __init__(self, **source_data):
        super().__init__(**source_data)
        self.sorting_extractor = self.SX(**source_data)
        self.writer_class = map_si_object_to_writer(self.sorting_extractor)

    def subset_sorting(self):
        """
        Subset a recording extractor according to stub and channel subset options.

        Parameters
        ----------
        stub_test : bool, optional (default False)
        """
        self.writer_class = map_si_object_to_writer(self.sorting_extractor)(
            self.sorting_extractor,
            stub=True,
        )

    def run_conversion(
        self,
        nwbfile: NWBFile,
        metadata: dict,
        stub_test: bool = False,
        write_ecephys_metadata: bool = False,
        save_path: OptionalPathType = None,
        overwrite: bool = False,
        **kwargs,
    ):
        """
        Primary function for converting the data in a SortingExtractor to the NWB standard.

        Parameters
        ----------
        nwbfile: NWBFile
            nwb file to which the recording information is to be added
        metadata: dict
            metadata info for constructing the nwb file (optional).
            Should be of the format
                metadata['Ecephys']['UnitProperties'] = dict(name=my_name, description=my_description)
        stub_test: bool, optional (default False)
            If True, will truncate the data to run the conversion faster and take up less memory.
        write_ecephys_metadata: bool (optional, defaults to False)
            Write electrode information contained in the metadata.
        save_path: PathType
            Required if an nwbfile is not passed. Must be the path to the nwbfile
            being appended, otherwise one is created and written.
        overwrite: bool
            If using save_path, whether or not to overwrite the NWBFile if it already exists.
        skip_unit_features: list
            list of unit feature names to skip writing to units table.
        skip_unit_properties: list
            list of unit properties to skip writing to units table.
        unit_property_descriptions: dict
            custom descriptions for unit properties:
            >>> dict(prop_name='description')
            the Other way to add custom descrptions is to override the default metadata:
            >>> metadata = self.get_metadata()
            >>> metadata.update(Units=[dict(name='prop_name1', description='description1'),
            >>>                        dict(name='prop_name1', description='description1')])
        """
        if stub_test:
            self.subset_sorting()
        if write_ecephys_metadata and "Ecephys" in metadata:

            class TempEcephysInterface(BaseRecordingExtractorInterface):
                RX = se.NumpyRecordingExtractor

            n_channels = max([len(x["data"]) for x in metadata["Ecephys"]["Electrodes"]])
            temp_ephys = TempEcephysInterface(timeseries=np.array(range(n_channels)), sampling_frequency=1)
            temp_ephys.run_conversion(nwbfile=nwbfile, metadata=metadata, write_electrical_series=False)

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
