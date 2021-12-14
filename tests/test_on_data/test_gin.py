import tempfile
import unittest
import os
import pytest
import numpy.testing as npt
from pathlib import Path

from spikeextractors import NwbRecordingExtractor, NwbSortingExtractor
from spikeextractors.testing import check_recordings_equal, check_sortings_equal
from roiextractors import NwbImagingExtractor, NwbSegmentationExtractor
from roiextractors.testing import check_imaging_equal, check_segmentations_equal
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
    TiffImagingInterface,
    Hdf5ImagingInterface,
    SbxImagingInterface,
    CaimanSegmentationInterface,
    CnmfeSegmentationInterface,
    ExtractSegmentationInterface,
    Suite2pSegmentationInterface,
)

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
    LOCAL_PATH = Path("./")  # Override this on personal device for local testing
    print("Running GIN tests locally!")

ECEPHYS_DATA_PATH = LOCAL_PATH / "ephy_testing_data"
HAVE_ECEPHYS_DATA = ECEPHYS_DATA_PATH.exists()
OPHYS_DATA_PATH = LOCAL_PATH / "ophys_testing_data"
HAVE_OPHYS_DATA = OPHYS_DATA_PATH.exists()

if not HAVE_PARAMETERIZED:
    pytest.fail("parameterized module is not installed! Please install (`pip install parameterized`).")

if not HAVE_ECEPHYS_DATA:
    pytest.fail(f"No ephy_testing_data folder found in location: {ECEPHYS_DATA_PATH}!")

if not OPHYS_DATA_PATH:
    pytest.fail(f"No oephys_testing_data folder found in location: {OPHYS_DATA_PATH}!")


def custom_name_func(testcase_func, param_num, param):
    return (
        f"{testcase_func.__name__}_{param_num}_"
        f"{parameterized.to_safe_name(param.kwargs['data_interface'].__name__)}"
    )


class TestEcephysNwbConversions(unittest.TestCase):
    savedir = Path(tempfile.mkdtemp())

    parameterized_recording_list = [
        param(
            data_interface=NeuralynxRecordingInterface,
            interface_kwargs=dict(
                folder_path=str(ECEPHYS_DATA_PATH / "neuralynx" / "Cheetah_v5.7.4" / "original_data")
            ),
        ),
        param(
            data_interface=NeuroscopeRecordingInterface,
            interface_kwargs=dict(file_path=str(ECEPHYS_DATA_PATH / "neuroscope" / "test1" / "test1.dat")),
        ),
        param(
            data_interface=OpenEphysRecordingExtractorInterface,
            interface_kwargs=dict(
                folder_path=str(ECEPHYS_DATA_PATH / "openephysbinary" / "v0.4.4.1_with_video_tracking")
            ),
        ),
        param(
            data_interface=BlackrockRecordingExtractorInterface,
            interface_kwargs=dict(filename=str(ECEPHYS_DATA_PATH / "blackrock" / "FileSpec2.3001.ns5")),
        ),
        param(
            recording_interface=AxonaRecordingExtractorInterface,
            interface_kwargs=dict(file_path=str(ECEPHYS_DATA_PATH / "axona" / "axona_raw.bin")),
        ),
        param(
            recording_interface=AxonaLFPDataInterface,
            interface_kwargs=dict(file_path=str(ECEPHYS_DATA_PATH / "axona" / "dataset_unit_spikes" / "20140815-180secs.eeg")),
        ),
    ]
    for suffix in ["rhd", "rhs"]:
        parameterized_recording_list.append(
            param(
                data_interface=IntanRecordingInterface,
                interface_kwargs=dict(file_path=str(ECEPHYS_DATA_PATH / "intan" / f"intan_{suffix}_test_1.{suffix}")),
            )
        )
    for file_name, num_channels in zip(["20210225_em8_minirec2_ac", "W122_06_09_2019_1_fromSD"], [512, 128]):
        for gains in [None, [0.195], [0.385] * num_channels]:
            interface_kwargs = dict(filename=str(ECEPHYS_DATA_PATH / "spikegadgets" / f"{file_name}.rec"))
            if gains is not None:
                interface_kwargs.update(gains=gains)
            parameterized_recording_list.append(
                param(
                    data_interface=SpikeGadgetsRecordingInterface,
                    interface_kwargs=interface_kwargs,
                )
            )
    for suffix in ["ap", "lf"]:
        sub_path = Path("spikeglx") / "Noise4Sam_g0" / "Noise4Sam_g0_imec0"
        parameterized_recording_list.append(
            param(
                data_interface=SpikeGLXRecordingInterface,
                interface_kwargs=dict(
                    file_path=str(ECEPHYS_DATA_PATH / sub_path / f"Noise4Sam_g0_t0.imec0.{suffix}.bin")
                ),
            )
        )

    @parameterized.expand(parameterized_recording_list, name_func=custom_name_func)
    def test_convert_recording_extractor_to_nwb(self, data_interface, interface_kwargs):
        nwbfile_path = str(self.savedir / f"{data_interface.__name__}.nwb")

        class TestConverter(NWBConverter):
            data_interface_classes = dict(TestRecording=data_interface)

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
                data_interface=PhySortingInterface,
                interface_kwargs=dict(folder_path=str(ECEPHYS_DATA_PATH / "phy" / "phy_example_0")),
            ),
            param(
                data_interface=BlackrockSortingExtractorInterface,
                interface_kwargs=dict(filename=str(ECEPHYS_DATA_PATH / "blackrock" / "FileSpec2.3001.nev")),
            ),
        ],
        name_func=custom_name_func,
    )
    def test_convert_sorting_extractor_to_nwb(self, data_interface, interface_kwargs):
        nwbfile_path = str(self.savedir / f"{data_interface.__name__}.nwb")

        class TestConverter(NWBConverter):
            data_interface_classes = dict(TestSorting=data_interface)

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


class TestOphysNwbConversions(unittest.TestCase):
    savedir = Path(tempfile.mkdtemp())

    imaging_interface_list = [
        param(
            data_interface=TiffImagingInterface,
            interface_kwargs=dict(
                file_path=str(OPHYS_DATA_PATH / "imaging_datasets" / "Tif" / "demoMovie.tif"),
                sampling_frequency=15.0,  # typically provied by user
            ),
        ),
        param(
            data_interface=Hdf5ImagingInterface,
            interface_kwargs=dict(file_path=str(OPHYS_DATA_PATH / "imaging_datasets" / "hdf5" / "demoMovie.hdf5")),
        ),
    ]
    for suffix in [".mat", ".sbx"]:
        imaging_interface_list.append(
            param(
                data_interface=SbxImagingInterface,
                interface_kwargs=dict(
                    file_path=str(OPHYS_DATA_PATH / "imaging_datasets" / "Scanbox" / f"sample{suffix}")
                ),
            ),
        )

    @parameterized.expand(imaging_interface_list, name_func=custom_name_func)
    def test_convert_imaging_extractor_to_nwb(self, data_interface, interface_kwargs):
        nwbfile_path = str(self.savedir / f"{data_interface.__name__}.nwb")

        class TestConverter(NWBConverter):
            data_interface_classes = dict(TestImaging=data_interface)

            def get_metadata(self):
                metadata = super().get_metadata()
                # attach device to ImagingPlane lacking property
                device_name = metadata["Ophys"]["Device"][0]["name"]
                if "device" not in metadata["Ophys"]["ImagingPlane"][0].keys():
                    metadata["Ophys"]["ImagingPlane"][0]["device"] = device_name
                # attach ImagingPlane to TwoPhotonSeries lacking property
                plane_name = metadata["Ophys"]["ImagingPlane"][0]["name"]
                if "imaging_plane" not in metadata["Ophys"]["TwoPhotonSeries"][0].keys():
                    metadata["Ophys"]["TwoPhotonSeries"][0]["imaging_plane"] = plane_name

                return metadata

        converter = TestConverter(source_data=dict(TestImaging=dict(interface_kwargs)))
        converter.run_conversion(nwbfile_path=nwbfile_path, overwrite=True)
        imaging = converter.data_interface_objects["TestImaging"].imaging_extractor
        nwb_imaging = NwbImagingExtractor(file_path=nwbfile_path)
        check_imaging_equal(img1=imaging, img2=nwb_imaging)

    @parameterized.expand(
        [
            param(
                data_interface=CaimanSegmentationInterface,
                interface_kwargs=dict(
                    file_path=str(OPHYS_DATA_PATH / "segmentation_datasets" / "caiman" / "caiman_analysis.hdf5")
                ),
            ),
            param(
                data_interface=CnmfeSegmentationInterface,
                interface_kwargs=dict(
                    file_path=str(
                        OPHYS_DATA_PATH
                        / "segmentation_datasets"
                        / "cnmfe"
                        / "2014_04_01_p203_m19_check01_cnmfeAnalysis.mat"
                    )
                ),
            ),
            param(
                data_interface=ExtractSegmentationInterface,
                interface_kwargs=dict(
                    file_path=str(
                        OPHYS_DATA_PATH
                        / "segmentation_datasets"
                        / "extract"
                        / "2014_04_01_p203_m19_check01_extractAnalysis.mat"
                    )
                ),
            ),
            param(
                data_interface=Suite2pSegmentationInterface,
                interface_kwargs=dict(
                    # TODO: argument name is 'file_path' on roiextractors, but it clearly refers to a folder_path
                    file_path=str(OPHYS_DATA_PATH / "segmentation_datasets" / "suite2p" / "plane0")
                ),
            ),
        ],
        name_func=custom_name_func,
    )
    def test_convert_segmentation_extractor_to_nwb(self, data_interface, interface_kwargs):
        nwbfile_path = str(self.savedir / f"{data_interface.__name__}.nwb")

        class TestConverter(NWBConverter):
            data_interface_classes = dict(TestSegmentation=data_interface)

        converter = TestConverter(source_data=dict(TestSegmentation=dict(interface_kwargs)))
        converter.run_conversion(nwbfile_path=nwbfile_path, overwrite=True)
        segmentation = converter.data_interface_objects["TestSegmentation"].segmentation_extractor
        nwb_segmentation = NwbSegmentationExtractor(file_path=nwbfile_path)
        check_segmentations_equal(seg1=segmentation, seg2=nwb_segmentation)


if __name__ == "__main__":
    unittest.main()
