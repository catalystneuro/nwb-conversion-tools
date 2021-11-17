import shutil
import tempfile
import unittest
from pathlib import Path
import numpy as np
from datetime import datetime
from warnings import warn

from pynwb import NWBHDF5IO, NWBFile

from nwb_conversion_tools.utils import export_ecephys_to_nwb, SI090NwbEphysWriter, create_si090_example
from spikeinterface.core.testing import check_sortings_equal, check_recordings_equal
from spikeinterface.extractors import NwbRecordingExtractor, NwbSortingExtractor
from spikeinterface import extract_waveforms


class TestExtractors(unittest.TestCase):
    def setUp(self):
        self.RX, self.SX = create_si090_example()
        self.RX2, self.SX2 = create_si090_example()
        self.RX3, self.SX3 = create_si090_example()
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        del self.RX, self.RX2, self.RX3, self.SX, self.SX2, self.SX3
        shutil.rmtree(self.test_dir)

    def test_write_recording(self):
        path = self.test_dir + "/test.nwb"

        export_ecephys_to_nwb(self.RX, path)
        RX_nwb = NwbRecordingExtractor(path)
        check_recordings_equal(self.RX, RX_nwb, return_scaled=False)
        del RX_nwb

        export_ecephys_to_nwb(object_to_write=self.RX2, nwb_file_path=path, overwrite=True)
        RX_nwb = NwbRecordingExtractor(path)
        check_recordings_equal(self.RX2, RX_nwb, return_scaled=False)

        # Writing multiple recordings using metadata
        path_multi = self.test_dir + "/test_multiple.nwb"
        nwbfile = export_ecephys_to_nwb(
            object_to_write=self.RX,
            nwb_file_path=path_multi,
            write_as="raw",
        )
        nwbfile = export_ecephys_to_nwb(
            object_to_write=self.RX2,
            nwbfile=nwbfile,
            write_as="processed",
            overwrite=False,
        )
        nwbfile = export_ecephys_to_nwb(
            object_to_write=self.RX3, nwbfile=nwbfile, write_as="lfp", es_key="ElectricalSeries_lfp", overwrite=False
        )
        es_raw_name = "ElectricalSeries"
        RX_nwb = NwbRecordingExtractor(file_path=path_multi, electrical_series_name=es_raw_name)
        check_recordings_equal(self.RX, RX_nwb, return_scaled=False)
        del RX_nwb

        nwbfile = export_ecephys_to_nwb(
            object_to_write=self.RX, nwb_file_path=path, overwrite=True
        )  # Testing default compression, should be "gzip"
        with NWBHDF5IO(path=path, mode="r") as io:
            nwbfile = io.read()
            compression_out = nwbfile.acquisition[es_raw_name].data.compression
        self.assertEqual(
            compression_out,
            "gzip",
            f"Intended compression type does not match what was written! (Out: {compression_out}, should be: gzip)",
        )
        RX_nwb = NwbRecordingExtractor(path)
        check_recordings_equal(self.RX, RX_nwb, return_scaled=False)
        del RX_nwb

        compression = "lzf"
        export_ecephys_to_nwb(object_to_write=self.RX, nwb_file_path=path, overwrite=True, compression=compression)
        with NWBHDF5IO(path=path, mode="r") as io:
            nwbfile = io.read()
            compression_out = nwbfile.acquisition[es_raw_name].data.compression
        self.assertEqual(
            compression_out,
            compression,
            f"Intended compression type does not match what was written! (Out: {compression_out}, should be: {compression})",
        )
        RX_nwb = NwbRecordingExtractor(path)
        check_recordings_equal(self.RX, RX_nwb, return_scaled=False)
        del RX_nwb

    def test_write_sorting(self):
        path = self.test_dir + "/test.nwb"
        sf = self.RX.get_sampling_frequency()

        # Append sorting to existing file
        nwbfile = export_ecephys_to_nwb(object_to_write=self.RX)
        _ = export_ecephys_to_nwb(object_to_write=self.SX, nwbfile=nwbfile)
        with NWBHDF5IO(str(path), mode="w") as io:
            io.write(nwbfile)
        SX_nwb = NwbSortingExtractor(path)
        check_sortings_equal(self.SX, SX_nwb)

        # Test for handling unit property descriptions argument
        property_descriptions = dict(stability="This is a description of stability.")
        nwbfile = export_ecephys_to_nwb(
            object_to_write=self.SX,
            nwb_file_path=path,
            unit_property_descriptions=property_descriptions,
            overwrite=True,
        )
        SX_nwb = NwbSortingExtractor(path, sampling_frequency=sf)
        check_sortings_equal(self.SX, SX_nwb)

        # Test for handling skip_properties argument
        nwbfile = export_ecephys_to_nwb(
            object_to_write=self.SX, nwb_file_path=path, skip_unit_properties=["stability"], overwrite=True
        )
        SX_nwb = NwbSortingExtractor(path, sampling_frequency=sf)
        assert "stability" not in SX_nwb.get_property_keys()
        check_sortings_equal(self.SX, SX_nwb)

    def test_write_waveforms(self):
        path = self.test_dir + "/test_wf.nwb"
        # set is_filtered=True for waveforms
        self.RX.annotate(is_filtered=True)
        we = extract_waveforms(self.RX, self.SX, folder=Path(self.test_dir) / "waveforms")

        nwbfile = export_ecephys_to_nwb(object_to_write=we, nwb_file_path=path, overwrite=True)

        assert "waveform_mean" in nwbfile.units.colnames
        assert "waveform_sd" in nwbfile.units.colnames

        # check waveform_mean and sd shapes
        assert nwbfile.units["waveform_mean"][0].shape[1] == self.RX.get_num_channels()
        assert nwbfile.units["waveform_sd"][0].shape[1] == self.RX.get_num_channels()
        assert nwbfile.units["waveform_mean"][0].shape[0] == nwbfile.units["waveform_sd"][0].shape[0]


class TestWriteElectrodes(unittest.TestCase):
    def setUp(self):
        self.RX, self.SX = create_si090_example()
        self.RX2, self.SX2 = create_si090_example()
        self.RX3, self.SX3 = create_si090_example()
        self.test_dir = tempfile.mkdtemp()
        self.path1 = self.test_dir + "/test_electrodes1.nwb"
        self.path2 = self.test_dir + "/test_electrodes2.nwb"
        self.path3 = self.test_dir + "/test_electrodes3.nwb"
        self.nwbfile1 = NWBFile("sess desc1", "file id1", datetime.now())
        self.metadata_list = [dict(Ecephys={i: dict(name=i, description="desc")}) for i in ["es1", "es2"]]
        # change channel_ids
        id_offset = np.max(self.RX.get_channel_ids())
        self.RX2 = self.RX2.channel_slice(
            self.RX2.get_channel_ids(), renamed_channel_ids=np.array(self.RX2.get_channel_ids()) + id_offset + 1
        )

        self.RX2.set_channel_groups(np.ones(shape=self.RX2.get_num_channels(), dtype="int"))
        self.RX.set_channel_groups(np.zeros(shape=self.RX.get_num_channels(), dtype="int"))
        self.SX.set_property("electrode_group", ["0"] * self.SX.get_num_units())
        # add common properties:
        self.RX2.set_property("prop1", ["10Hz"] * self.RX2.get_num_channels())
        self.RX.set_property("prop1", ["10Hz"] * self.RX.get_num_channels())
        self.RX2.set_property("brain_area", ["M1"] * self.RX2.get_num_channels())
        self.RX.set_property("brain_area", ["PMd"] * self.RX.get_num_channels())
        self.RX2.set_property("group_electrodes", ["M1"] * self.RX2.get_num_channels())
        self.RX.set_property("group_electrodes", ["PMd"] * self.RX.get_num_channels())
        rx2_alt_ch_ids = []
        rx1_alt_ch_ids = []
        for no, (chan_id1, chan_id2) in enumerate(zip(self.RX.get_channel_ids(), self.RX2.get_channel_ids())):
            if no % 2 == 0:
                rx1_alt_ch_ids.append(chan_id1)
                rx2_alt_ch_ids.append(chan_id2)
        self.RX.set_property("prop2", values=np.array(rx1_alt_ch_ids).astype(float), ids=rx1_alt_ch_ids)
        self.RX2.set_property("prop2", values=np.array(rx2_alt_ch_ids).astype(float), ids=rx2_alt_ch_ids)

        self.RX.set_property("prop3", [str(i) for i in rx1_alt_ch_ids], rx1_alt_ch_ids)
        self.RX2.set_property("prop3", [str(i) for i in rx2_alt_ch_ids], rx2_alt_ch_ids)

    def test_append_same_properties(self):
        export_ecephys_to_nwb(
            object_to_write=self.RX, nwbfile=self.nwbfile1, metadata=self.metadata_list[0], es_key="es1"
        )
        export_ecephys_to_nwb(
            object_to_write=self.RX2, nwbfile=self.nwbfile1, metadata=self.metadata_list[1], es_key="es2"
        )
        export_ecephys_to_nwb(object_to_write=self.SX, nwbfile=self.nwbfile1)
        with NWBHDF5IO(str(self.path1), "w") as io:
            io.write(self.nwbfile1)
        with NWBHDF5IO(str(self.path1), "r") as io:
            nwb = io.read()
            assert all(
                nwb.electrodes.id.data[()] == np.concatenate((self.RX.get_channel_ids(), self.RX2.get_channel_ids()))
            )
            assert all([i in nwb.electrodes.colnames for i in ["prop1", "prop2", "prop3"]])
            for i, chan_id in enumerate(nwb.electrodes.id.data):
                assert nwb.electrodes["prop1"][i] == "10Hz"
                if chan_id in self.RX.get_channel_ids():
                    assert nwb.electrodes["location"][i] == "PMd"
                    assert nwb.electrodes["group_name"][i] == "0"
                    assert nwb.electrodes["group"][i].name == "0"
                else:
                    assert nwb.electrodes["location"][i] == "M1"
                    assert nwb.electrodes["group_name"][i] == "1"
                    assert nwb.electrodes["group"][i].name == "1"
                if i % 2 == 0:
                    assert nwb.electrodes["prop2"][i] == chan_id
                    assert nwb.electrodes["prop3"][i] == str(chan_id)
                else:
                    assert np.isnan(nwb.electrodes["prop2"][i])
                    assert nwb.electrodes["prop3"][i] == ""

            # check for units table:
            assert "electrode_group" in nwb.units
            for no, unit_id in enumerate(nwb.units.id.data):
                assert nwb.units["electrode_group"][no].name == "0"

    def test_different_channel_properties(self):
        _ = self.RX2._properties.pop("prop2")
        self.RX2.set_property("prop_new", self.RX2.get_channel_ids())
        export_ecephys_to_nwb(
            object_to_write=self.RX, nwbfile=self.nwbfile1, metadata=self.metadata_list[0], es_key="es1"
        )
        export_ecephys_to_nwb(
            object_to_write=self.RX2, nwbfile=self.nwbfile1, metadata=self.metadata_list[1], es_key="es2"
        )
        with NWBHDF5IO(str(self.path1), "w") as io:
            io.write(self.nwbfile1)
        with NWBHDF5IO(str(self.path1), "r") as io:
            nwb = io.read()
            for i, chan_id in enumerate(nwb.electrodes.id.data):
                if i < len(nwb.electrodes.id.data) / 2:
                    assert np.isnan(nwb.electrodes["prop_new"][i])
                    if i % 2 == 0:
                        assert nwb.electrodes["prop2"][i] == chan_id
                    else:
                        assert np.isnan(nwb.electrodes["prop2"][i])
                else:
                    assert np.isnan(nwb.electrodes["prop2"][i])
                    assert nwb.electrodes["prop_new"][i] == chan_id

    def test_group_set_custom_description(self):
        for i, (grp_name, grp_desc) in enumerate(zip(["0", "1"], ["PMd", "M1"])):
            self.metadata_list[i]["Ecephys"].update(
                ElectrodeGroup=[dict(name=grp_name, description=grp_desc + " description")]
            )
        export_ecephys_to_nwb(
            object_to_write=self.RX, nwbfile=self.nwbfile1, metadata=self.metadata_list[0], es_key="es1"
        )
        export_ecephys_to_nwb(
            object_to_write=self.RX2, nwbfile=self.nwbfile1, metadata=self.metadata_list[1], es_key="es2"
        )
        with NWBHDF5IO(str(self.path1), "w") as io:
            io.write(self.nwbfile1)
        with NWBHDF5IO(str(self.path1), "r") as io:
            nwb = io.read()
            for i, chan_id in enumerate(nwb.electrodes.id.data):
                if i < len(nwb.electrodes.id.data) / 2:
                    assert nwb.electrodes["group_name"][i] == "0"
                    assert nwb.electrodes["group"][i].description == "PMd description"
                else:
                    assert nwb.electrodes["group_name"][i] == "1"
                    assert nwb.electrodes["group"][i].description == "M1 description"
