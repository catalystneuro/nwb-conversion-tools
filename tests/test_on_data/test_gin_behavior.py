import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import pytest
from pynwb import NWBHDF5IO

from nwb_conversion_tools import NWBConverter, DeepLabCutInterface
from nwb_conversion_tools.utils import load_dict_from_file

try:
    import dlc2nwb

    HAVE_DLC2NWB = True
except ImportError:
    HAVE_DLC2NWB = False

try:
    from parameterized import parameterized, param

    HAVE_PARAMETERIZED = True
except ImportError:
    HAVE_PARAMETERIZED = False
# Load the configuration for the data tests
test_config_dict = load_dict_from_file(Path(__file__).parent / "gin_test_config.json")

# GIN dataset: https://gin.g-node.org/NeuralEnsemble/behavior_testing_data
if os.getenv("CI"):
    LOCAL_PATH = Path(".")  # Must be set to "." for CI
    print("Running GIN tests on Github CI!")
else:
    # Override LOCAL_PATH in the `gin_test_config.json` file to a point on your system that contains the dataset folder
    # Use DANDIHub at hub.dandiarchive.org for open, free use of data found in the /shared/catalystneuro/ directory
    LOCAL_PATH = Path(test_config_dict["LOCAL_PATH"])
    print("Running GIN tests locally!")
BEHAVIOR_DATA_PATH = LOCAL_PATH / "behavior_testing_data"
HAVE_DATA = BEHAVIOR_DATA_PATH.exists()

if test_config_dict["SAVE_OUTPUTS"]:
    OUTPUT_PATH = LOCAL_PATH / "example_nwb_output"
    OUTPUT_PATH.mkdir(exist_ok=True)
else:
    OUTPUT_PATH = Path(tempfile.mkdtemp())
if not HAVE_PARAMETERIZED:
    pytest.fail("parameterized module is not installed! Please install (`pip install parameterized`).")
if not HAVE_DATA:
    pytest.fail(f"No behavior_testing_data folder found in location: {BEHAVIOR_DATA_PATH}!")


def custom_name_func(testcase_func, param_num, param):
    return (
        f"{testcase_func.__name__}_{param_num}_"
        f"{parameterized.to_safe_name(param.kwargs['data_interface'].__name__)}"
    )


@unittest.skipIf(not HAVE_DLC2NWB, "dlc2nwb not installed")
class TestBehaviorNwbConversions(unittest.TestCase):
    savedir = OUTPUT_PATH

    @parameterized.expand(
        [
            param(
                data_interface=DeepLabCutInterface,
                interface_kwargs=dict(
                    dlc_file_path=str(
                        BEHAVIOR_DATA_PATH / "DLC" / "m3v1mp4DLC_resnet50_openfieldAug20shuffle1_30000.h5"
                    ),
                    config_file_path=str(BEHAVIOR_DATA_PATH / "DLC" / "config.yaml"),
                ),
            )
        ]
    )
    def test_convert_behaviordata_to_nwb(self, data_interface, interface_kwargs):
        nwbfile_path = self.savedir / f"{data_interface.__name__}.nwb"

        if nwbfile_path.exists():
            nwbfile_path = self.savedir / f"{data_interface.__name__}_2.nwb"

        class TestConverter(NWBConverter):
            data_interface_classes = dict(TestBehavior=data_interface)

        converter = TestConverter(source_data=dict(TestBehavior=dict(interface_kwargs)))
        metadata = converter.get_metadata()
        metadata["NWBFile"].update(session_start_time=datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S"))
        converter.run_conversion(nwbfile_path=nwbfile_path, overwrite=True, metadata=metadata)

        with NWBHDF5IO(path=nwbfile_path, mode="r", load_namespaces=True) as io:
            nwbfile = io.read()
            assert "behavior" in nwbfile.processing
            assert "PoseEstimation" in nwbfile.processing["behavior"].data_interfaces
            assert all(
                [
                    i in nwbfile.processing["behavior"].data_interfaces["PoseEstimation"].pose_estimation_series
                    for i in ["ind1_leftear", "ind1_rightear", "ind1_snout", "ind1_tailbase"]
                ]
            )
