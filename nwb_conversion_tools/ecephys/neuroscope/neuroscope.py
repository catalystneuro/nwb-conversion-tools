from nwb_conversion_tools.converter import NWBConverter
from pynwb import NWBFile
import uuid


class Neuroscope2NWB(NWBConverter):
    def __init__(self, nwbfile=None, metadata=None, source_paths=None):
        """
        Class that converts Neuroscope data to NWB.

        Parameters
        ----------
        nwbfile: pynwb.NWBFile
        metadata: dict
        """
        super().__init__(nwbfile=nwbfile, metadata=metadata, source_paths=source_paths)

    def create_nwbfile(self, metadata_nwbfile):
        """
        Overriding method to get session_start_time from neuroscope files.
        """
        nwbfile_args = dict(identifier=str(uuid.uuid4()),)
        nwbfile_args.update(**metadata_nwbfile)
        session_start_time = self.get_session_start_time()
        nwbfile_args.update(**session_start_time)
        self.nwbfile = NWBFile(**nwbfile_args)

    def get_session_start_time(self):
        """
        Gets session_start_time from Neuroscope files.
        """
        raise NotImplementedError('TODO')

    def run_conversion(self):
        """
        Runs conversion to nwbfile.
        """
        raise NotImplementedError('TODO')
