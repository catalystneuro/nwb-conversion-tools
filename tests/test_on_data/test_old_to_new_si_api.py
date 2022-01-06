import numpy.testing as npt
from os import getenv
from unittest import TestCase
from pathlib import Path

from spikeinterface.core.old_api_utils import create_recording_from_old_extractor, OldToNewRecording

from nwb_conversion_tools import SpikeGLXLFPInterface

# Path to dataset downloaded from https://gin.g-node.org/NeuralEnsemble/ephy_testing_data
#   ecephys: https://gin.g-node.org/NeuralEnsemble/ephy_testing_data
#   ophys: TODO
#   icephys: TODO
if getenv("CI"):
    LOCAL_PATH = Path(".")  # Must be set to "." for CI
    print("Running GIN tests on Github CI!")
else:
    LOCAL_PATH = Path("/home/jovyan/")  # Override this on personal device for local testing
    print("Running GIN tests locally!")

DATA_PATH = LOCAL_PATH / "ephy_testing_data"
HAVE_DATA = DATA_PATH.exists()


class TestNwbConversions(TestCase):
    def test_spikeglx_lfp_create_old_to_new_method(self):
        interface = SpikeGLXLFPInterface(
            file_path=str(
                DATA_PATH / "spikeglx" / "Noise4Sam_g0" / "Noise4Sam_g0_imec0" / "Noise4Sam_g0_t0.imec0.lf.bin"
            )
        )
        initial_properties = interface.recording_extractor.get_shared_channel_property_names()
        for member in ["channel_name", "gain", "group", "offset", "shank_electrode_number", "shank_group_name"]:
            self.assertIn(member=member, container=initial_properties)
        new_recording = create_recording_from_old_extractor(oldapi_recording_extractor=interface.recording_extractor)
        new_properties = new_recording.get_property_keys()
        for member in set(initial_properties).union(["location", "gain_to_uV"]) - set(["gain", "offset"]):
            self.assertIn(member=member, container=new_properties)

        initial_locations = interface.recording_extractor.get_channel_locations()
        new_locations = new_recording.get_channel_locations()
        npt.assert_array_equal(x=initial_locations, y=new_locations)

    def test_spikeglx_lfp_init_old_to_new_class(self):
        interface = SpikeGLXLFPInterface(
            file_path=str(
                DATA_PATH / "spikeglx" / "Noise4Sam_g0" / "Noise4Sam_g0_imec0" / "Noise4Sam_g0_t0.imec0.lf.bin"
            )
        )
        initial_properties = interface.recording_extractor.get_shared_channel_property_names()
        for member in ["channel_name", "gain", "group", "offset", "shank_electrode_number", "shank_group_name"]:
            self.assertIn(member=member, container=initial_properties)
        new_recording = OldToNewRecording(oldapi_recording_extractor=interface.recording_extractor)
        new_properties = new_recording.get_property_keys()
        for member in set(initial_properties).union(["location", "gain_to_uV"]) - set(["gain", "offset"]):
            self.assertIn(member=member, container=new_properties)

        initial_locations = interface.recording_extractor.get_channel_locations()
        new_locations = new_recording.get_channel_locations()
        npt.assert_array_equal(x=initial_locations, y=new_locations)
