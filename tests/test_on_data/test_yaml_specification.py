import unittest
import os
from pathlib import Path
from datetime import datetime
from tempfile import mkdtemp
from shutil import rmtree

import pytest
from pynwb import NWBHDF5IO

from nwb_conversion_tools.utils.conversion_tools import run_conversion_from_yaml

# Path to dataset downloaded from https://gin.g-node.org/NeuralEnsemble/ephy_testing_data
#   ecephys: https://gin.g-node.org/NeuralEnsemble/ephy_testing_data
#   ophys: TODO
#   icephys: TODO
if os.getenv("CI"):
    LOCAL_PATH = Path(".")  # Must be set to "." for CI
    print("Running GIN tests on Github CI!")
else:
    LOCAL_PATH = Path("/home/jovyan/")  # Override this on personal device for local testing
    print("Running GIN tests locally!")

DATA_PATH = LOCAL_PATH / "ephy_testing_data"
HAVE_DATA = DATA_PATH.exists()

if not HAVE_DATA:
    pytest.fail(f"No ephy_testing_data folder found in location: {DATA_PATH}!")


class TestYAML(unittest.TestCase):
    def setUp(self):
        self.test_folder = Path(mkdtemp())

    def tearDown(self):
        rmtree(path=self.test_folder)

    def test_run_conversion_from_yaml(self):
        path_to_test_gin_file = Path(__file__)
        yaml_file_path = path_to_test_gin_file.parent / "GIN_converter_specification.yml"
        run_conversion_from_yaml(
            specification_file_path=yaml_file_path,
            data_folder=DATA_PATH,
            output_folder=self.test_folder,
            overwrite=True,
        )

        with NWBHDF5IO(path=self.test_folder / "example_converter_spec_1.nwb", mode="r") as io:
            nwbfile = io.read()
            assert nwbfile.session_description == "Subject navigating a Y-shaped maze."
            assert nwbfile.lab == "My Lab"
            assert nwbfile.institution == "My Institution"
            assert nwbfile.session_start_time == datetime.fromisoformat("2020-10-09T21:19:09+00:00")
            assert nwbfile.subject.subject_id == "1"
            assert "ElectricalSeries" in nwbfile.acquisition
        with NWBHDF5IO(path=self.test_folder / "example_converter_spec_2.nwb", mode="r") as io:
            nwbfile = io.read()
            assert nwbfile.session_description == "Subject navigating a Y-shaped maze."
            assert nwbfile.lab == "My Lab"
            assert nwbfile.institution == "My Institution"
            assert nwbfile.session_start_time == datetime.fromisoformat("2020-10-10T21:19:09+00:00")
            assert nwbfile.subject.subject_id == "002"
            assert "ElectricalSeries" in nwbfile.acquisition
        with NWBHDF5IO(path=self.test_folder / "example_converter_spec_3.nwb", mode="r") as io:
            nwbfile = io.read()
            assert nwbfile.session_description == "no description"
            assert nwbfile.lab == "My Lab"
            assert nwbfile.institution == "My Institution"
            assert nwbfile.session_start_time == datetime.fromisoformat("2020-10-11T21:19:09+00:00")
            assert nwbfile.subject.subject_id == "Subject Name"
            assert "ElectricalSeries" in nwbfile.acquisition
            assert "spike_times" in nwbfile.units


if __name__ == "__main__":
    unittest.main()
