from unittest import TestCase, skip
import numpy as np
from tempfile import mkdtemp
from shutil import rmtree
from pathlib import Path

from pynwb.base import ProcessingModule
from spikeextractors import NumpyRecordingExtractor

from nwb_conversion_tools.utils.nwbfile_tools import get_module, make_nwbfile_from_metadata
from nwb_conversion_tools.utils.conversion_tools import (
    check_regular_timestamps,
    reverse_fstring_path,
    collect_reverse_fstring_files,
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

    # @skip("to be implemented")
    # def test_estimate_recording_conversion_time(self):
    #     num_channels = 4
    #     sampling_frequency = 30000
    #     num_frames = sampling_frequency * 1
    #     timeseries = np.random.randint(low=-32768, high=32767, size=[num_channels, num_frames], dtype=np.dtype("int16"))
    #     recording = NumpyRecordingExtractor(timeseries=timeseries, sampling_frequency=sampling_frequency)

    #     estimated_write_time, estimated_write_speed = estimate_recording_conversion_time(recording=recording)
    #     estimated_write_time, estimated_write_speed = estimate_recording_conversion_time(
    #         recording=recording, write_kwargs=dict(compression=None)
    #     )


class TestDatasetInference(TestCase):
    def setUp(self):
        self.tmpdir = Path(mkdtemp())
        self.temp_dataset_folder_path = self.tmpdir / "TestDatasetInference"
        self.temp_dataset_folder_path.mkdir()

        self.n_sessions = 4
        self.n_subjects_per_session = 3
        subject_counter = 0
        for session_num in range(1, self.n_sessions + 1):
            session_folder_path_str = f"sess_{session_num}"
            session_folder_path = self.temp_dataset_folder_path / session_folder_path_str
            session_folder_path.mkdir()
            for _ in range(self.n_subjects_per_session):
                subject_folder_path_str = f"subj_{subject_counter}"
                subject_folder_path = session_folder_path / subject_folder_path_str
                subject_folder_path.mkdir()
                file_path = subject_folder_path / f"{session_folder_path_str}_{subject_folder_path_str}.dat"
                np.memmap(filename=file_path, dtype="uint8", mode="write", shape=(4, 4))
                subject_counter += 1

    def tearDown(self):
        rmtree(path=self.tmpdir)

    def test_reverse_fstring_start_end_path_slash(self):
        true_output = dict(session_id=[1], subject_id=[2])
        for sample_string in [
            "MyFolder/{session_id}/{subject_id}",
            "/MyFolder/{session_id}/{subject_id}",
            "MyFolder/{session_id}/{subject_id}/",
            "/MyFolder/{session_id}/{subject_id}/",
        ]:
            info = reverse_fstring_path(string=sample_string)
            self.assertDictEqual(d1=true_output, d2=info)

    def test_reverse_f_string_repetition(self):
        true_output = dict(session_id=[1, 3], subject_id=[2])
        info = reverse_fstring_path(string="/MyFolder/{session_id}/{subject_id}/{session_id}_test.txt")
        self.assertDictEqual(d1=true_output, d2=info)

    def test_collect_reverse_fstring_files(self):
        true_output = []
        subject_counter = 0
        for session_num in range(1, self.n_sessions + 1):
            for _ in range(self.n_subjects_per_session):
                session_id = f"sess_{session_num}"
                subject_id = f"subj_{subject_counter}"
                subject_counter += 1
                true_output.append(
                    dict(
                        path=self.temp_dataset_folder_path / session_id / subject_id,
                        session_id=session_id,
                        subject_id=subject_id,
                    )
                )
        folder_paths = collect_reverse_fstring_files(
            string=str(self.temp_dataset_folder_path / "{session_id}" / "{subject_id}")
        )
        for member in folder_paths:
            self.assertIn(member=member, container=true_output)
