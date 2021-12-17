import shutil
import tempfile
import unittest
from pathlib import Path
import numpy as np
from datetime import datetime
from warnings import warn

import spikeextractors as se
from spikeextractors.testing import (
    check_sortings_equal,
    check_recordings_equal,
    check_dumping,
    check_recording_return_types,
    get_default_nwbfile_metadata,
)
from pynwb import NWBHDF5IO, NWBFile

from nwb_conversion_tools.utils import export_ecephys_to_nwb, SI013NwbEphysWriter, create_si013_example


class TestExtractors(unittest.TestCase):
    def setUp(self):
        self.RX, self.RX2, self.RX3, self.SX, self.SX2, self.SX3, self.example_info = create_si013_example(seed=0)
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        del self.RX, self.RX2, self.RX3, self.SX, self.SX2, self.SX3
        shutil.rmtree(self.test_dir)

    def test_write_recording_stub(self):
        path = self.test_dir + "/test.nwb"
        export_ecephys_to_nwb(self.RX, path, stub=True)
        RX_nwb = se.NwbRecordingExtractor(path)
        # the stub is the trimmed recording in time dimension.
        frame_stub = min(100, self.RX.get_num_frames())
        rx_stub = se.SubRecordingExtractor(self.RX, end_frame=frame_stub)
        check_recordings_equal(rx_stub, RX_nwb)

    def test_write_sorting_stub(self):
        path = self.test_dir + "/test.nwb"
        export_ecephys_to_nwb(self.SX, path, stub=True)
        sf = self.RX.get_sampling_frequency()
        SX_nwb = se.NwbSortingExtractor(path, sampling_frequency=sf)
        max_min_spike_time = max(
            [min(x) for y in self.SX.get_unit_ids() for x in [self.SX.get_unit_spike_train(y)] if any(x)]
        )
        sx_stub = se.SubSortingExtractor(self.SX, start_frame=0, end_frame=1.1*max_min_spike_time)
        check_sortings_equal(sx_stub, SX_nwb)

    def test_write_recording(self):
        path = self.test_dir + "/test.nwb"

        export_ecephys_to_nwb(self.RX, path)
        RX_nwb = se.NwbRecordingExtractor(path)
        check_recording_return_types(RX_nwb)
        check_recordings_equal(self.RX, RX_nwb, check_times=False)
        check_dumping(RX_nwb)
        del RX_nwb

        export_ecephys_to_nwb(object_to_write=self.RX2, nwb_file_path=path, overwrite=True)
        RX_nwb = se.NwbRecordingExtractor(path)
        check_recording_return_types(RX_nwb)
        check_recordings_equal(self.RX2, RX_nwb, check_times=False)
        check_dumping(RX_nwb)

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
        RX_nwb = se.NwbRecordingExtractor(file_path=path_multi, electrical_series_name=es_raw_name)
        check_recording_return_types(RX_nwb)
        check_recordings_equal(self.RX, RX_nwb, check_times=False)
        check_dumping(RX_nwb)
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
        RX_nwb = se.NwbRecordingExtractor(path)
        check_recording_return_types(RX_nwb)
        check_recordings_equal(self.RX, RX_nwb, check_times=False)
        check_dumping(RX_nwb)
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
        RX_nwb = se.NwbRecordingExtractor(path)
        check_recording_return_types(RX_nwb)
        check_recordings_equal(self.RX, RX_nwb, check_times=False)
        check_dumping(RX_nwb)
        del RX_nwb

    def test_write_sorting(self):
        path = self.test_dir + "/test.nwb"
        sf = self.RX.get_sampling_frequency()

        # Append sorting to existing file
        nwbfile = export_ecephys_to_nwb(object_to_write=self.RX)
        _ = export_ecephys_to_nwb(object_to_write=self.SX, nwbfile=nwbfile)
        with NWBHDF5IO(str(path), mode="w") as io:
            io.write(nwbfile)
        SX_nwb = se.NwbSortingExtractor(path)
        check_sortings_equal(self.SX, SX_nwb)
        check_dumping(SX_nwb)

        # Test for handling unit property descriptions argument
        property_descriptions = dict(stability="This is a description of stability.")
        nwbfile = export_ecephys_to_nwb(
            object_to_write=self.SX,
            nwb_file_path=path,
            unit_property_descriptions=property_descriptions,
            overwrite=True,
        )
        SX_nwb = se.NwbSortingExtractor(path, sampling_frequency=sf)
        check_sortings_equal(self.SX, SX_nwb)
        check_dumping(SX_nwb)

        # Test for handling skip_properties argument
        nwbfile = export_ecephys_to_nwb(
            object_to_write=self.SX, nwb_file_path=path, skip_unit_properties=["stability"], overwrite=True
        )
        SX_nwb = se.NwbSortingExtractor(path, sampling_frequency=sf)
        assert "stability" not in SX_nwb.get_shared_unit_property_names()
        check_sortings_equal(self.SX, SX_nwb)
        check_dumping(SX_nwb)

        # Test for handling skip_features argument
        # SX2 has timestamps, so loading it back from Nwb will not recover the same spike frames. Set use_times=False
        nwbfile = export_ecephys_to_nwb(
            object_to_write=self.SX2, nwb_file_path=path, skip_unit_features=["widths"], use_times=False, overwrite=True
        )
        SX_nwb = se.NwbSortingExtractor(path, sampling_frequency=sf)
        assert "widths" not in SX_nwb.get_shared_unit_spike_feature_names()
        check_sortings_equal(self.SX2, SX_nwb)
        check_dumping(SX_nwb)

    def check_metadata_write(self, metadata: dict, nwbfile_path: Path, recording: se.RecordingExtractor):
        writer = SI013NwbEphysWriter(recording, nwb_file_path=nwbfile_path)
        standard_metadata = writer.get_nwb_metadata()
        device_defaults = dict(name="Device", description="no description")  # from the individual add_devices function
        electrode_group_defaults = dict(  # from the individual add_electrode_groups function
            name="Electrode Group", description="no description", location="unknown", device="Device"
        )

        with NWBHDF5IO(path=nwbfile_path, mode="r", load_namespaces=True) as io:
            nwbfile = io.read()

            device_source = metadata["Ecephys"].get("Device", standard_metadata["Ecephys"]["Device"])
            self.assertEqual(len(device_source), len(nwbfile.devices))
            for device in device_source:
                device_name = device.get("name", device_defaults["name"])
                self.assertIn(device_name, nwbfile.devices)
                self.assertEqual(
                    device.get("description", device_defaults["description"]), nwbfile.devices[device_name].description
                )
                self.assertEqual(device.get("manufacturer"), nwbfile.devices[device["name"]].manufacturer)

            electrode_group_source = metadata["Ecephys"].get(
                "ElectrodeGroup", standard_metadata["Ecephys"]["ElectrodeGroup"]
            )
            self.assertEqual(len(electrode_group_source), len(nwbfile.electrode_groups))
            for group in electrode_group_source:
                group_name = group.get("name", electrode_group_defaults["name"])
                self.assertIn(group_name, nwbfile.electrode_groups)
                self.assertEqual(
                    group.get("description", electrode_group_defaults["description"]),
                    nwbfile.electrode_groups[group_name].description,
                )
                self.assertEqual(
                    group.get("location", electrode_group_defaults["location"]),
                    nwbfile.electrode_groups[group_name].location,
                )
                device_name = group.get("device", electrode_group_defaults["device"])
                self.assertIn(device_name, nwbfile.devices)
                self.assertEqual(nwbfile.electrode_groups[group_name].device, nwbfile.devices[device_name])

            n_channels = len(recording.get_channel_ids())
            electrode_source = metadata["Ecephys"].get("Electrodes", [])
            self.assertEqual(n_channels, len(nwbfile.electrodes))
            for column in electrode_source:
                column_name = column["name"]
                self.assertIn(column_name, nwbfile.electrodes)
                self.assertEqual(column["description"], getattr(nwbfile.electrodes, column_name).description)
                if column_name in ["x", "y", "z", "rel_x", "rel_y", "rel_z"]:
                    for j in n_channels:
                        self.assertEqual(column["data"][j], getattr(nwbfile.electrodes[j], column_name).values[0])
                else:
                    for j in n_channels:
                        self.assertTrue(
                            column["data"][j] == getattr(nwbfile.electrodes[j], column_name).values[0]
                            or (
                                np.isnan(column["data"][j])
                                and np.isnan(getattr(nwbfile.electrodes[j], column_name).values[0])
                            )
                        )


class TestWriteElectrodes(unittest.TestCase):
    def setUp(self):
        self.RX, self.RX2, _, self.SX, _, _, _ = create_si013_example(seed=0)
        self.test_dir = tempfile.mkdtemp()
        self.path1 = self.test_dir + "/test_electrodes1.nwb"
        self.path2 = self.test_dir + "/test_electrodes2.nwb"
        self.path3 = self.test_dir + "/test_electrodes3.nwb"
        self.nwbfile1 = NWBFile("sess desc1", "file id1", datetime.now())
        self.nwbfile2 = NWBFile("sess desc2", "file id2", datetime.now())
        self.nwbfile3 = NWBFile("sess desc3", "file id3", datetime.now())
        self.metadata_list = [dict(Ecephys={i: dict(name=i, description="desc")}) for i in ["es1", "es2"]]
        # change channel_ids
        id_offset = np.max(self.RX.get_channel_ids())
        self.RX2 = se.subrecordingextractor.SubRecordingExtractor(
            self.RX2, renamed_channel_ids=np.array(self.RX2.get_channel_ids()) + id_offset + 1
        )
        self.RX2.set_channel_groups(np.ones(shape=self.RX2.get_num_channels(), dtype="int"))
        self.RX.set_channel_groups(np.zeros(shape=self.RX.get_num_channels(), dtype="int"))
        for unit_id in self.SX.get_unit_ids():
            self.SX.set_unit_property(unit_id, "electrode_group", "0")
        # add common properties:
        for no, (chan_id1, chan_id2) in enumerate(zip(self.RX.get_channel_ids(), self.RX2.get_channel_ids())):
            self.RX2.set_channel_property(chan_id2, "prop1", "10Hz")
            self.RX.set_channel_property(chan_id1, "prop1", "10Hz")
            self.RX2.set_channel_property(chan_id2, "brain_area", "M1")
            self.RX.set_channel_property(chan_id1, "brain_area", "PMd")
            self.RX2.set_channel_property(chan_id2, "group_electrodes", "M1")
            self.RX.set_channel_property(chan_id1, "group_electrodes", "PMd")
            if no % 2 == 0:
                self.RX2.set_channel_property(chan_id2, "prop2", chan_id2)
                self.RX.set_channel_property(chan_id1, "prop2", chan_id1)
                self.RX2.set_channel_property(chan_id2, "prop3", str(chan_id2))
                self.RX.set_channel_property(chan_id1, "prop3", str(chan_id1))

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
            assert all(nwb.electrodes.id.data[()] == np.array(self.RX.get_channel_ids() + self.RX2.get_channel_ids()))
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
        for chan_id in self.RX2.get_channel_ids():
            self.RX2.clear_channel_property(chan_id, "prop2")
            self.RX2.set_channel_property(chan_id, "prop_new", chan_id)
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


if __name__ == "__main__":
    unittest.main()
