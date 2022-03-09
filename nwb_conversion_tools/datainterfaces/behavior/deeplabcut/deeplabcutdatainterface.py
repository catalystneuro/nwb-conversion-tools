"""Authors: Saksham Sharda, Cody Baker, Ben Dichter."""

from ....basedatainterface import BaseDataInterface
from ....utils import FilePathType

try:
    from dlc2nwb.utils import write_subject_to_nwb, auxiliaryfunctions

    HAVE_DLC2NWB = True
except ImportError:
    HAVE_DLC2NWB = False


class DeepLabCutInterface(BaseDataInterface):
    """Data interface for DeepLabCut datasets"""

    def __init__(self, dlc_file_path: FilePathType, config_file_path: FilePathType, subject_name: str):
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
        super().__init__(dlc_file_path=dlc_file_path, config_file_path=config_file_path)

    def get_metadata(self):
        metadata = dict(
            NWBFile=dict(session_description=self._config_file["Task"], experimenter=[self._config_file["scorer"]]),
            Subject=dict(subject_id=self.subject_name),
        )
        return metadata

    def run_conversion(self, nwbfile, metadata: dict):
        """
        Conversion from DLC output files to nwb. Derived from dlc2nwb library.

        Parameters
        ----------
        nwbfile: pynwb.NWBFile
        metadata: dict

        """
        write_subject_to_nwb(
            nwbfile, self.source_data["dlc_file_path"], self.subject_name, self.source_data["config_file_path"]
        )
