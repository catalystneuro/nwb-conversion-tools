"""Author: Ben Dichter."""
from typing import Optional

from pynwb import NWBFile
from pynwb.device import Device
from pynwb.ophys import ImagingPlane, TwoPhotonSeries

from ...basedatainterface import BaseDataInterface
from ...tools.roiextractors import write_imaging, get_nwb_imaging_metadata
from ...utils import (
    get_schema_from_hdmf_class,
    fill_defaults,
    get_base_schema,
    OptionalFilePathType,
)


class BaseImagingExtractorInterface(BaseDataInterface):
    IX = None

    def __init__(self, verbose=True, **source_data):
        super().__init__(**source_data)
        self.imaging_extractor = self.IX(**source_data)
        self.verbose = verbose

    def get_metadata_schema(self):
        metadata_schema = super().get_metadata_schema()
        self.imaging_extractor._sampling_frequency = float(self.imaging_extractor._sampling_frequency)

        metadata_schema["required"] = ["Ophys"]

        # Initiate Ophys metadata
        metadata_schema["properties"]["Ophys"] = get_base_schema(tag="Ophys")
        metadata_schema["properties"]["Ophys"]["required"] = ["Device", "ImagingPlane", "TwoPhotonSeries"]
        metadata_schema["properties"]["Ophys"]["properties"] = dict(
            Device=dict(type="array", minItems=1, items={"$ref": "#/properties/Ophys/properties/definitions/Device"}),
            ImagingPlane=dict(
                type="array", minItems=1, items={"$ref": "#/properties/Ophys/properties/definitions/ImagingPlane"}
            ),
            TwoPhotonSeries=dict(
                type="array", minItems=1, items={"$ref": "#/properties/Ophys/properties/definitions/TwoPhotonSeries"}
            ),
        )

        # Schema definition for arrays
        metadata_schema["properties"]["Ophys"]["properties"]["definitions"] = dict(
            Device=get_schema_from_hdmf_class(Device),
            ImagingPlane=get_schema_from_hdmf_class(ImagingPlane),
            TwoPhotonSeries=get_schema_from_hdmf_class(TwoPhotonSeries),
        )

        fill_defaults(metadata_schema, self.get_metadata())
        return metadata_schema

    def get_metadata(self):
        metadata = super().get_metadata()
        metadata.update(get_nwb_imaging_metadata(self.imaging_extractor))
        _ = metadata.pop("NWBFile")

        # fix troublesome data types
        if "TwoPhotonSeries" in metadata["Ophys"]:
            for two_photon_series in metadata["Ophys"]["TwoPhotonSeries"]:
                if "dimension" in two_photon_series:
                    two_photon_series["dimension"] = list(two_photon_series["dimension"])
                if "rate" in two_photon_series:
                    two_photon_series["rate"] = float(two_photon_series["rate"])
        return metadata

    def run_conversion(
        self,
        nwbfile_path: OptionalFilePathType = None,
        nwbfile: Optional[NWBFile] = None,
        metadata: Optional[dict] = None,
        overwrite: bool = False,
        stub_test: bool = False,
        save_path: OptionalFilePathType = None,  # TODO deprecate on or after Aug 1
    ):
        """
        Primary function for converting raw (unprocessed) RecordingExtractor data to the NWB standard.

        nwbfile_path: FilePathType
            Path for where to write or load (if overwrite=False) the NWBFile.
            If specified, this context will always write to this location.
        nwbfile: NWBFile
            nwb file to which the recording information is to be added
        metadata: dict
            metadata info for constructing the nwb file (optional).
            Should be of the format::

                metadata['Ecephys']['ElectricalSeries'] = dict(name=my_name, description=my_description)
        overwrite: bool, optional
            Whether or not to overwrite the NWBFile if one exists at the nwbfile_path.
        The default is False (append mode).
        starting_time: float (optional)
            Sets the starting time of the ElectricalSeries to a manually set value.
            Increments timestamps if use_times is True.
        use_times: bool
            If True, the times are saved to the nwb file using recording.frame_to_time(). If False (default),
            the sampling rate is used.
        stub_test: bool, optional (default False)
            If True, will truncate the data to run the conversion faster and take up less memory.

        """
        if stub_test:
            end_frame = max(self.imaging_extractor.get_frame_size()) + 1
            imaging = self.imaging_extractor.frame_slice(start_frame=0, end_frame=end_frame)
        else:
            imaging = self.imaging_extractor

        write_imaging(
            imaging=imaging,
            nwbfile_path=nwbfile_path,
            nwbfile=nwbfile,
            metadata=metadata,
            overwrite=overwrite,
            verbose=self.verbose,
            save_path=save_path,
        )
