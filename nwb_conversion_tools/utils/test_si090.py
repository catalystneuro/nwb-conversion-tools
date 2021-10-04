import shutil
import tempfile
import unittest
from pathlib import Path
import numpy as np
from datetime import datetime
from warnings import warn

from pynwb import NWBHDF5IO, NWBFile

from nwb_conversion_tools.utils import export_ecephys_to_nwb, SI090NwbEphysWriter, create_si090_example


class TestExtractors(unittest.TestCase):
    def setUp(self):
        self.RX, self.SX = create_si090_example(seed=0)
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        del self.RX, self.SX
        shutil.rmtree(self.test_dir)

    def test_write_recording(self):
        path = self.test_dir + "/test.nwb"

        export_ecephys_to_nwb(self.RX, path)
        RX_nwb = se.NwbRecordingExtractor(path)
