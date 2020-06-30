from pathlib import Path
import yaml
import unittest
from pynwb import NWBHDF5IO
from nwb_conversion_tools.gui.nwb_conversion_gui import nwb_conversion_gui
from nwb_conversion_tools.ophys.CELLMax.CELLMax import CellMax2NWB

here = str(Path(__file__).parent.absolute())


class TestCellMax(unittest.TestCase):

    def test_script(self):
        metafile = here + r'\datasets\nct_ophys_metafile_CellMax.yaml'
        fileloc = here + r'\datasets\2014_04_01_p203_m19_check01_emAnalysis.mat'
        nwbloc = here + r'\datasets\test_nwb_em.nwb'
        with open(metafile) as f:
            metadata = yaml.safe_load(f)

        cellmaxobj = CellMax2NWB(fileloc, None, metadata)

        cellmaxobj.run_conversion()

        cellmaxobj.save(nwbloc)
        with NWBHDF5IO(nwbloc, 'r') as f:
            nwbfile = f.read()


class TestCellMaxGui(unittest.TestCase):
    def test_gui(self):
        metafile = here + r'\datasets\nct_ophys_metafile_CellMax.yaml'
        fileloc = here + r'\datasets\2014_04_01_p203_m19_check01_emAnalysis.mat'
        source_paths = dict(cnmfe_path=dict(type='file', path=fileloc))

        kwargs_fields = {}

        nwb_conversion_gui(
            metafile=metafile,
            conversion_class=CellMax2NWB,
            source_paths=source_paths,
            kwargs_fields=kwargs_fields
        )