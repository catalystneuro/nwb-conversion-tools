"""Heberto Mayorquin, Authors: Saksham Sharda, Cody Baker, Ben Dichter."""
from typing import Optional

from pynwb.file import NWBFile

from ....basedatainterface import BaseDataInterface
from nwb_conversion_tools.utils import dict_deep_update
from nwb_conversion_tools.utils import FilePathType, OptionalFilePathType
from nwb_conversion_tools.tools.nwb_helpers import make_or_load_nwbfile

try:
    from dlc2nwb.utils import auxiliaryfunctions, write_subject_to_nwb

    HAVE_DLC2NWB = True
except ImportError:
    HAVE_DLC2NWB = False


class DeepLabCutInterface(BaseDataInterface):
    """Data interface for DeepLabCut datasets"""

    def __init__(
        self,
        dlc_file_path: FilePathType,
        config_file_path: FilePathType,
        subject_name: str = "ind1",
        verbose: bool = True,
    ):
        """
        Interface for writing DLC's h5 files to nwb using dlc2nwb.
        Parameters
        ----------
        dlc_file_path: FilePathType
            path to the h5 file output by dlc.
        config_file_path: FilePathType
            path to .yml config file
        """
        if "DLC" not in dlc_file_path or not dlc_file_path.endswith(".h5"):
            raise IOError("The file passed in is not a DeepLabCut h5 data file.")
        assert HAVE_DLC2NWB, "to use this datainterface: 'pip install dlc2nwb'"
        self._config_file = auxiliaryfunctions.read_config(config_file_path)
        self.subject_name = subject_name
        self.verbose = verbose
        super().__init__(dlc_file_path=dlc_file_path, config_file_path=config_file_path)

    def get_metadata(self):
        metadata = dict(
            NWBFile=dict(session_description=self._config_file["Task"], experimenter=[self._config_file["scorer"]]),
        )
        return metadata

    def run_conversion(
        self,
        nwbfile_path: OptionalFilePathType = None,
        nwbfile: Optional[NWBFile] = None,
        metadata: Optional[dict] = None,
        overwrite: bool = False,
    ):
        """
        Conversion from DLC output files to nwb. Derived from dlc2nwb library.
        Parameters
        ----------
        nwbfile: pynwb.NWBFile
        metadata: dict
        """

        base_metadata = self.get_metadata()
        metadata = dict_deep_update(base_metadata, metadata)

        with make_or_load_nwbfile(
            nwbfile_path=nwbfile_path, nwbfile=nwbfile, metadata=metadata, overwrite=overwrite, verbose=self.verbose
        ) as nwbfile_out:
            write_subject_to_nwb(
                nwbfile=nwbfile_out,
                h5file=str(self.source_data["dlc_file_path"]),
                individual_name=self.subject_name,
                config_file=self.source_data["config_file_path"],
            )
