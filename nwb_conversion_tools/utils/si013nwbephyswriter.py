import warnings
from numbers import Real
from typing import Union

import numpy as np
import pynwb

from .basesinwbephyswriter import BaseSINwbEphysWriter

try:
    import spikeextractors as se

    HAVE_SI013 = True
except ImportError:
    HAVE_SI013 = False


class SI013NwbEphysWriter(BaseSINwbEphysWriter):
    """
    Class to write RecordingExtractor and SortingExtractor object from SI<=0.13 to NWB

    Parameters
    ----------
    object_to_write: se.RecordingExtractor or se.SortingExtractor
    stub: bool
        whether to write a subset of recording extractor traces array as electrical series in nwbfile
    stub_channels: list
        channels to include when writing as stub
    """

    def __init__(self, object_to_write, stub=False, stub_channels=None):
        assert HAVE_SI013, "spikeextractors 0.13 version not installed"
        BaseSINwbEphysWriter.__init__(self, object_to_write, stub=stub, stub_channels=stub_channels)
        if isinstance(self.object_to_write, se.RecordingExtractor):
            self.recording = self.object_to_write
            if self.stub:
                self._make_recording_stub()
        elif isinstance(self.object_to_write, se.SortingExtractor):
            self.sorting = self.object_to_write
            if self.stub:
                self._make_sorting_stub()

    def _make_recording_stub(self):
        if self.stub_channels is not None:
            channel_stub = self.stub_channels
        else:
            num_channels = min(10, self.recording.get_num_channels())
            channel_stub = self.recording.get_channel_ids()[:num_channels]
        frame_stub = min(100, self.recording.get_num_frames())
        self.recording = se.SubRecordingExtractor(self.recording, channel_ids=channel_stub, end_frame=frame_stub)

    def _make_sorting_stub(self):
        max_min_spike_time = max(
            [min(x) for y in self.sorting.get_unit_ids() for x in [self.sorting.get_unit_spike_train(y)] if any(x)]
        )
        self.sorting = se.SubSortingExtractor(self.sorting, start_frame=0, end_frame=1.1 * max_min_spike_time)

    @staticmethod
    def supported_types():
        assert HAVE_SI013
        return se.RecordingExtractor, se.SortingExtractor

    def get_num_segments(self):
        return 1

    def _get_traces(self, channel_ids=None, start_frame=None, end_frame=None, return_scaled=True, segment_index=0):
        return self.recording.get_traces(
            channel_ids=channel_ids, start_frame=start_frame, end_frame=end_frame, return_scaled=return_scaled
        ).T

    def _get_dtype(self, return_scaled=True):
        return self.recording.get_dtype(return_scaled)

    def _get_channel_property_names(self):
        property_names = set()
        for chan_id in self._get_channel_ids():
            for i in self.recording.get_channel_property_names(chan_id):
                property_names.add(i)
        return list(property_names)

    def _fill_missing_property_values(self, channel_ids, prop, get_prop_func, get_prop_names_func):
        self.dt_column_defaults = {list: [], str: "", Real: np.nan, np.ndarray: np.array([np.nan])}
        # find the size of ndarray dtype:
        for chan_id in channel_ids:
            if prop not in get_prop_names_func(chan_id):
                continue
            id_data = get_prop_func(chan_id, prop)
            if isinstance(id_data, np.ndarray):
                self.dt_column_defaults.update({np.ndarray: np.nan * np.ones(shape=[1, *id_data.shape[1:]])})
                break
            else:
                break
        # find the channel property dtype:
        found_property_types = Real
        for chan_id in channel_ids:
            if prop not in get_prop_names_func(chan_id):
                continue
            id_data = get_prop_func(chan_id, prop)
            proptype = [proptype for proptype in self.dt_column_defaults if isinstance(id_data, proptype)]
            if len(proptype) > 0:
                found_property_types = proptype[0]
                break
            else:  # if property not found in the supported self.dt_column_defaults, then return None
                return
        # build data array:
        data = []
        for chan_id in channel_ids:
            if prop not in get_prop_names_func(chan_id):
                id_data = self.dt_column_defaults[found_property_types]
            else:
                id_data = get_prop_func(chan_id, prop)
            if found_property_types == Real:
                data.append(np.float(id_data))
            else:
                data.append(id_data)
        return np.array(data)

    def _get_channel_property_values(self, prop):
        assert isinstance(prop, str), "prop name must be a string"
        if prop == "location":
            return self.recording.get_channel_locations()
        elif prop == "gain":
            return self.recording.get_channel_gains()
        elif prop == "offset":
            return self.recording.get_channel_offsets()
        elif prop == "group":
            if any(
                [
                    "group_name" in self.recording.get_channel_property_names(id)
                    for id in self.recording.get_channel_ids()
                ]
            ):
                prop_values = self._fill_missing_property_values(
                    self._get_channel_ids(),
                    "group_name",
                    self.recording.get_channel_property,
                    self.recording.get_channel_property_names,
                )
                return self._check_valid_property(prop_values)
            return self.recording.get_channel_groups()
        else:
            prop_values = self._fill_missing_property_values(
                self._get_channel_ids(),
                prop,
                self.recording.get_channel_property,
                self.recording.get_channel_property_names,
            )
            return self._check_valid_property(prop_values)

    def _get_num_frames(self, segment_index=0):
        return self.recording.get_num_frames()

    def _get_recording_times(self, segment_index=0):
        return self.recording.frame_to_time(np.arange(0, self._get_num_frames()))

    def _get_unit_feature_names(self):
        unit_ids = self._get_unit_ids()
        all_features = set()
        for unit_id in unit_ids:
            all_features.update(self.sorting.get_unit_spike_feature_names(unit_id))
        return list(all_features)

    def _get_unit_feature_values(self, prop):
        feat_values = self._fill_missing_property_values(
            self._get_unit_ids(), prop, self.sorting.get_unit_spike_features, self.sorting.get_unit_spike_feature_names
        )
        return self._check_valid_property(feat_values)

    def _get_unit_spike_train_ids(self, unit_id, start_frame=None, end_frame=None, segment_index=None):
        return self.sorting.get_unit_spike_train(unit_id, start_frame=start_frame, end_frame=end_frame)

    def _get_unit_spike_train_times(self, unit_id, segment_index=0):
        return self.sorting.frame_to_time(self.sorting.get_unit_spike_train(unit_id=unit_id))

    def _get_unit_property_names(self):
        property_names = set()
        for unit_id in self._get_unit_ids():
            for i in self.sorting.get_unit_property_names(unit_id):
                property_names.add(i)
        return list(property_names)

    def _get_unit_property_values(self, prop):
        prop_values = self._fill_missing_property_values(
            self._get_unit_ids(), prop, self.sorting.get_unit_property, self.sorting.get_unit_property_names
        )
        return self._check_valid_property(prop_values)

    def _get_unit_waveforms_templates(self, unit_id, mode="mean"):
        if "template" in self._get_unit_property_names():
            template = self._get_unit_property_values("template")
            if len(template) > 0:
                if mode == "mean":
                    return template.T  # (samples, no_channels)
                elif mode == "std":
                    return

    def add_epochs(self):
        """
        Auxiliary static method for nwbextractor.

        Adds epochs from recording object to nwbfile object.

        """
        if self.nwbfile is not None:
            assert isinstance(self.nwbfile, pynwb.NWBFile), "'nwbfile' should be of type pynwb.NWBFile"

        # add/update epochs
        for epoch_name in self.recording.get_epoch_names():
            epoch = self.recording.get_epoch_info(epoch_name)
            if self.nwbfile.epochs is None:
                self.nwbfile.add_epoch(
                    start_time=self.recording.frame_to_time(epoch["start_frame"]),
                    stop_time=self.recording.frame_to_time(epoch["end_frame"] - 1),
                    tags=epoch_name,
                )
            else:
                if [epoch_name] in self.nwbfile.epochs["tags"][:]:
                    ind = self.nwbfile.epochs["tags"][:].index([epoch_name])
                    self.nwbfile.epochs["start_time"].data[ind] = self.recording.frame_to_time(epoch["start_frame"])
                    self.nwbfile.epochs["stop_time"].data[ind] = self.recording.frame_to_time(epoch["end_frame"])
                else:
                    self.nwbfile.add_epoch(
                        start_time=self.recording.frame_to_time(epoch["start_frame"]),
                        stop_time=self.recording.frame_to_time(epoch["end_frame"]),
                        tags=epoch_name,
                    )

    def add_recording(self, segment_index=0):
        super().add_recording(segment_index=segment_index)
        if self._conversion_ops["write_electrical_series"]:
            self.add_epochs()
