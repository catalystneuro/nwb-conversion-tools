import tempfile
import unittest
import os
import numpy.testing as npt
from pathlib import Path
from datetime import datetime
from tempfile import mkdtemp
from shutil import rmtree

import pytest
from spikeextractors import NwbRecordingExtractor, NwbSortingExtractor
from spikeextractors.testing import check_recordings_equal, check_sortings_equal
from pynwb import NWBHDF5IO

from nwb_conversion_tools import (
    NWBConverter,
    IntanRecordingInterface,
    NeuralynxRecordingInterface,
    NeuroscopeRecordingInterface,
    OpenEphysRecordingExtractorInterface,
    PhySortingInterface,
    SpikeGadgetsRecordingInterface,
    SpikeGLXRecordingInterface,
    BlackrockRecordingExtractorInterface,
    BlackrockSortingExtractorInterface,
    AxonaRecordingExtractorInterface,
    AxonaLFPDataInterface,
)
from nwb_conversion_tools.utils.conversion_tools import run_conversion_from_yaml

try:
    from parameterized import parameterized, param

    HAVE_PARAMETERIZED = True
except ImportError:
    HAVE_PARAMETERIZED = False

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

if not HAVE_PARAMETERIZED:
    pytest.fail("parameterized module is not installed! Please install (`pip install parameterized`).")

if not HAVE_DATA:
    pytest.fail(f"No ephy_testing_data folder found in location: {DATA_PATH}!")


def custom_name_func(testcase_func, param_num, param):
    return (
        f"{testcase_func.__name__}_{param_num}_"
        f"{parameterized.to_safe_name(param.kwargs['recording_interface'].__name__)}"
    )


class TestNwbConversions(unittest.TestCase):
    savedir = Path(tempfile.mkdtemp())

    parameterized_recording_list = [
        param(
            recording_interface=NeuralynxRecordingInterface,
            interface_kwargs=dict(folder_path=str(DATA_PATH / "neuralynx" / "Cheetah_v5.7.4" / "original_data")),
        ),
        param(
            recording_interface=NeuroscopeRecordingInterface,
            interface_kwargs=dict(file_path=str(DATA_PATH / "neuroscope" / "test1" / "test1.dat")),
        ),
        param(
            recording_interface=OpenEphysRecordingExtractorInterface,
            interface_kwargs=dict(folder_path=str(DATA_PATH / "openephysbinary" / "v0.4.4.1_with_video_tracking")),
        ),
        param(
            recording_interface=BlackrockRecordingExtractorInterface,
            interface_kwargs=dict(file_path=str(DATA_PATH / "blackrock" / "FileSpec2.3001.ns5")),
        ),
        param(
            recording_interface=AxonaRecordingExtractorInterface,
            interface_kwargs=dict(file_path=str(DATA_PATH / "axona" / "axona_raw.bin")),
        ),
        param(
            recording_interface=AxonaLFPDataInterface,
            interface_kwargs=dict(file_path=str(DATA_PATH / "axona" / "dataset_unit_spikes" / "20140815-180secs.eeg")),
        ),
    ]
    for suffix in ["rhd", "rhs"]:
        parameterized_recording_list.append(
            param(
                recording_interface=IntanRecordingInterface,
                interface_kwargs=dict(file_path=str(DATA_PATH / "intan" / f"intan_{suffix}_test_1.{suffix}")),
            )
        )
    for file_name, num_channels in zip(["20210225_em8_minirec2_ac", "W122_06_09_2019_1_fromSD"], [512, 128]):
        for gains in [None, [0.195], [0.385] * num_channels]:
            interface_kwargs = dict(file_path=str(DATA_PATH / "spikegadgets" / f"{file_name}.rec"))
            if gains is not None:
                interface_kwargs.update(gains=gains)
            parameterized_recording_list.append(
                param(
                    recording_interface=SpikeGadgetsRecordingInterface,
                    interface_kwargs=interface_kwargs,
                )
            )
    for suffix in ["ap", "lf"]:
        sub_path = Path("spikeglx") / "Noise4Sam_g0" / "Noise4Sam_g0_imec0"
        parameterized_recording_list.append(
            param(
                recording_interface=SpikeGLXRecordingInterface,
                interface_kwargs=dict(file_path=str(DATA_PATH / sub_path / f"Noise4Sam_g0_t0.imec0.{suffix}.bin")),
            )
        )

    @parameterized.expand(parameterized_recording_list)
    def test_convert_recording_extractor_to_nwb(self, recording_interface, interface_kwargs):
        nwbfile_path = str(self.savedir / f"{recording_interface.__name__}.nwb")

        class TestConverter(NWBConverter):
            data_interface_classes = dict(TestRecording=recording_interface)

        converter = TestConverter(source_data=dict(TestRecording=dict(interface_kwargs)))
        for interface_kwarg in interface_kwargs:
            if interface_kwarg in ["file_path", "folder_path"]:
                self.assertIn(
                    member=interface_kwarg, container=converter.data_interface_objects["TestRecording"].source_data
                )
        converter.run_conversion(nwbfile_path=nwbfile_path, overwrite=True)
        recording = converter.data_interface_objects["TestRecording"].recording_extractor
        nwb_recording = NwbRecordingExtractor(file_path=nwbfile_path)
        check_recordings_equal(RX1=recording, RX2=nwb_recording, check_times=False, return_scaled=False)
        check_recordings_equal(RX1=recording, RX2=nwb_recording, check_times=False, return_scaled=True)
        # Technically, check_recordings_equal only tests a snippet of data. Above tests are for metadata mostly.
        # For GIN test data, sizes should be OK to load all into RAM even on CI
        npt.assert_array_equal(
            x=recording.get_traces(return_scaled=False), y=nwb_recording.get_traces(return_scaled=False)
        )

    @parameterized.expand(
        [
            param(
                sorting_interface=PhySortingInterface,
                interface_kwargs=dict(folder_path=str(DATA_PATH / "phy" / "phy_example_0")),
            ),
            (
                BlackrockSortingExtractorInterface,
                dict(file_path=str(DATA_PATH / "blackrock" / "FileSpec2.3001.nev")),
            ),
        ]
    )
    def test_convert_sorting_extractor_to_nwb(self, sorting_interface, interface_kwargs):
        nwbfile_path = str(self.savedir / f"{sorting_interface.__name__}.nwb")

        class TestConverter(NWBConverter):
            data_interface_classes = dict(TestSorting=sorting_interface)

        converter = TestConverter(source_data=dict(TestSorting=dict(interface_kwargs)))
        for interface_kwarg in interface_kwargs:
            if interface_kwarg in ["file_path", "folder_path"]:
                self.assertIn(
                    member=interface_kwarg, container=converter.data_interface_objects["TestSorting"].source_data
                )
        converter.run_conversion(nwbfile_path=nwbfile_path, overwrite=True)
        sorting = converter.data_interface_objects["TestSorting"].sorting_extractor
        sf = sorting.get_sampling_frequency()
        if sf is None:  # need to set dummy sampling frequency since no associated acquisition in file
            sf = 30000
            sorting.set_sampling_frequency(sf)
        nwb_sorting = NwbSortingExtractor(file_path=nwbfile_path, sampling_frequency=sf)
        check_sortings_equal(SX1=sorting, SX2=nwb_sorting)


class TestYAML(unittest.TestCase):
    def setUp(self):
        self.test_folder = Path(mkdtemp())

    def tearDown(self):
        rmtree(path=self.test_folder)

    def test_run_conversion_from_yaml(self):
        path_to_test_gin_file = Path(__file__)
        yaml_file_path = path_to_test_gin_file.parent / "GIN_converter_specification.yml"
        run_conversion_from_yaml(file_path=yaml_file_path, output_folder=self.test_folder, overwrite=True)

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
