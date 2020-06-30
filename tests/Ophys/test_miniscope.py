from nwb_conversion_tools.ophys.miniscope.miniscope import Miniscope2NWB
from pathlib import Path
import yaml
import unittest
from pynwb import NWBHDF5IO
from nwb_conversion_tools.gui.nwb_conversion_gui import nwb_conversion_gui


here = str(Path(__file__).parent.absolute())


class TestMiniscope(unittest.TestCase):

    def test_script(self):
        metafile = here + r'\datasets\nct_gui_out_basic.yml'
        fileloc = here + r'\datasets\example_miniscope'
        nwbloc = here + r'\datasets\test_nwb_miniscope.nwb'
        with open(metafile) as f:
            metadata = yaml.safe_load(f)

        miniscopeeobj = Miniscope2NWB(fileloc, None, metadata)

        miniscopeeobj.add_microscopy(fileloc)
        miniscopeeobj.add_behavior_video(fileloc)

        miniscopeeobj.save(nwbloc)
        with NWBHDF5IO(nwbloc, 'r') as f:
            nwbfile = f.read()

    def test_gui(self):
        metafile = here + r'\datasets\nct_gui_out_basic.yml'
        fileloc = here + r'\datasets\example_miniscope'
        source_paths = dict(miniscope_path=dict(type='folder', path=fileloc))
        with open(metafile) as f:
            metadata = yaml.safe_load(f)

        kwargs_fields = {}

        nwb_conversion_gui(
            metafile=metafile,
            conversion_class=Miniscope2NWB,
            source_paths=source_paths,
            kwargs_fields=kwargs_fields
        )

