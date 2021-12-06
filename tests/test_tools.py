from unittest import TestCase, skip
import numpy as np

from pynwb.base import ProcessingModule
from spikeextractors import NumpyRecordingExtractor

from nwb_conversion_tools.utils.nwbfile_tools import get_module, make_nwbfile_from_metadata
from nwb_conversion_tools.utils.conversion_tools import (
    check_regular_timestamps,
    estimate_recording_conversion_time,
    reverse_fstring,
    infer_path_levels,
)


class TestConversionTools(TestCase):
    def test_check_regular_timestamps(self):
        assert check_regular_timestamps([1, 2, 3])
        assert not check_regular_timestamps([1, 2, 4])

    def test_get_module(self):
        nwbfile = make_nwbfile_from_metadata(metadata=dict())

        name_1 = "test_1"
        name_2 = "test_2"
        description_1 = "description_1"
        description_2 = "description_2"
        nwbfile.create_processing_module(name=name_1, description=description_1)
        mod_1 = get_module(nwbfile=nwbfile, name=name_1, description=description_1)
        mod_2 = get_module(nwbfile=nwbfile, name=name_2, description=description_2)
        assert isinstance(mod_1, ProcessingModule)
        assert mod_1.description == description_1
        assert isinstance(mod_2, ProcessingModule)
        assert mod_2.description == description_2
        self.assertWarns(UserWarning, get_module, **dict(nwbfile=nwbfile, name=name_1, description=description_2))

    @skip("to be implemented")
    def test_estimate_recording_conversion_time(self):
        num_channels = 4
        sampling_frequency = 30000
        num_frames = sampling_frequency * 1
        timeseries = np.random.randint(low=-32768, high=32767, size=[num_channels, num_frames], dtype=np.dtype("int16"))
        recording = NumpyRecordingExtractor(timeseries=timeseries, sampling_frequency=sampling_frequency)

        estimated_write_time, estimated_write_speed = estimate_recording_conversion_time(recording=recording)
        estimated_write_time, estimated_write_speed = estimate_recording_conversion_time(
            recording=recording, write_kwargs=dict(compression=None)
        )

    def test_reverse_fstring(self):
        sample_string = "MyFolder/{session_id}/{subject_id}"
        for sample_string in [
            "MyFolder/{session_id}/{subject_id}",
            "/MyFolder/{session_id}/{subject_id}",
            "MyFolder/{session_id}/{subject_id}/",
            "/MyFolder/{session_id}/{subject_id}/",
        ]:
            extracted_keywords = reverse_fstring(string=sample_string)
            self.assertEqual(extracted_keywords, ["session_id", "subject_id"])

    def test_infer_path_levels(self):
        for sample_string in [
            "MyFolder/{session_id}/{subject_id}",
            "/MyFolder/{session_id}/{subject_id}",
            "MyFolder/{session_id}/{subject_id}/",
            "/MyFolder/{session_id}/{subject_id}/",
        ]:
            levels = infer_path_levels(keys=["session_id", "subject_id"], string=sample_string)
            self.assertEqual(levels, [1, 2])
