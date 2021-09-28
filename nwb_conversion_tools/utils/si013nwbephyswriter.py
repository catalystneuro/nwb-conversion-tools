from numbers import Real
from typing import Union

import numpy as np
import pynwb

from .basesinwbephyswriter import BaseSINwbEphysWriter
from .common_writer_tools import default_return

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
    nwb_file_path: Path type
    nwbfile: pynwb.NWBFile or None
    metadata: dict or None
    **kwargs: list kwargs and meaning
    """

    def __init__(
        self,
        object_to_write,
        nwbfile: pynwb.NWBFile = None,
        metadata: dict = None,
        **kwargs,
    ):
        assert HAVE_SI013, "spikeextractors 0.13 version not installed"
        BaseSINwbEphysWriter.__init__(self, object_to_write, nwbfile=nwbfile, metadata=metadata, **kwargs)
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
        return (se.RecordingExtractor, se.SortingExtractor)

    def get_num_segments(self):
        return 1

    # @default_return([])
    def _get_traces(self, channel_ids=None, start_frame=None, end_frame=None, return_scaled=True, segment_index=0):
        return self.recording.get_traces(
            channel_ids=channel_ids, start_frame=start_frame, end_frame=end_frame, return_scaled=return_scaled
        ).T

    def _get_channel_property_names(self):
        property_names = set()
        for chan_id in self._get_channel_ids():
            for i in self.recording.get_channel_property_names(chan_id):
                property_names.add(i)
        return list(property_names)

    def _fill_missing_property_values(self, ids, prop, get_prop_func):
        self.dt_column_defaults = {list: [], str: "", Real: np.nan, np.ndarray: np.array([np.nan])}
        # find the size of ndarray dtype:
        for id in ids:
            try:
                id_data = get_prop_func(id, prop)
                if isinstance(id_data, np.ndarray):
                    self.dt_column_defaults.update({np.ndarray: np.nan * np.ones(shape=[1, id_data.shape[1:]])})
                    break
                else:
                    break
            except:
                continue
        # find the channel property dtype:
        found_property_types = Real
        for id in ids:
            try:
                id_data = get_prop_func(id, prop)
                proptype = [proptype for proptype in self.dt_column_defaults if isinstance(id_data, proptype)]
                if len(proptype) > 0:
                    found_property_types = proptype[0]
                    break
                else:  # if property not found in the supported self.dt_column_defaults, then return None
                    return
            except:
                continue
        # build data array:
        data = []
        for id in ids:
            try:
                id_data = get_prop_func(id, prop)
            except:
                id_data = self.dt_column_defaults[found_property_types]
            if found_property_types == Real:
                data.append(np.float(id_data))
            else:
                data.append(id_data)
        return np.array(data)

    # #@default_return([])
    def _get_channel_property_values(self, prop):
        if prop == "location":
            return self.recording.get_channel_locations()
        elif prop == "gain":
            return self.recording.get_channel_gains()
        elif prop == "offset":
            return self.recording.get_channel_offsets()
        elif prop == "group":
            return self.recording.get_channel_groups()
        else:
            prop_values = self._fill_missing_property_values(
                self._get_channel_ids(), prop, self.recording.get_channel_property
            )
            return self._check_valid_property(prop_values)

    # @default_return(None)
    def _get_num_frames(self, segment_index=0):
        return self.recording.get_num_frames()

    # @default_return([])
    def _get_recording_times(self, segment_index=0):
        if self.recording._times is None:
            return np.arange(0, self._get_num_frames() * self._get_sampling_frequency(), self._get_sampling_frequency())
        return self.recording._times

    def _get_unit_feature_names(self):
        unit_ids = self._get_unit_ids()
        all_features = set()
        for unit_id in unit_ids:
            all_features.update(self.sorting.get_unit_spike_feature_names(unit_id))
        return list(all_features)

    # @default_return([])
    def _get_unit_feature_values(self, prop):
        feat_values = self._fill_missing_property_values(
            self._get_unit_ids(), prop, self.sorting.get_unit_spike_features
        )
        return self._check_valid_property(feat_values)

    # @default_return([])
    def _get_unit_spike_train_ids(self, unit_id, start_frame=None, end_frame=None, segment_index=None):
        return self.sorting.get_unit_spike_train(unit_id, start_frame=start_frame, end_frame=end_frame)

    # @default_return([])
    def _get_unit_spike_train_times(self, unit_id, segment_index=0):
        return self.sorting.frame_to_time(self.sorting.get_unit_spike_train(unit_id=unit_id))

    def _get_unit_property_names(self):
        property_names = set()
        for unit_id in self._get_unit_ids():
            for i in self.sorting.get_unit_property_names(unit_id):
                property_names.add(i)
        return list(property_names)

    # @default_return([])
    def _get_unit_property_values(self, prop):
        prop_values = self._fill_missing_property_values(self._get_unit_ids(), prop, self.sorting.get_unit_property)
        return self._check_valid_property(prop_values)

    # @default_return(np.array([]))
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

    def add_recording(self):
        super().add_recording(segment_index=0)
        if self._conversion_ops["write_electrical_series"]:
            self.add_epochs()


def create_si013_example(seed):
    channel_ids = [0, 1, 2, 3]
    num_channels = 4
    num_frames = 10000
    num_ttls = 30
    sampling_frequency = 30000
    X = np.random.RandomState(seed=seed).normal(0, 1, (num_channels, num_frames))
    geom = np.random.RandomState(seed=seed).normal(0, 1, (num_channels, 2))
    X = (X * 100).astype(int)
    ttls = np.sort(np.random.permutation(num_frames)[:num_ttls])

    RX = se.NumpyRecordingExtractor(timeseries=X, sampling_frequency=sampling_frequency, geom=geom)
    RX.set_ttls(ttls)
    RX.set_channel_locations([0, 0], channel_ids=0)
    RX.add_epoch("epoch1", 0, 10)
    RX.add_epoch("epoch2", 10, 20)
    for i, channel_id in enumerate(RX.get_channel_ids()):
        RX.set_channel_property(channel_id=channel_id, property_name="shared_channel_prop", value=i)

    RX2 = se.NumpyRecordingExtractor(timeseries=X, sampling_frequency=sampling_frequency, geom=geom)
    RX2.copy_epochs(RX)
    times = np.arange(RX.get_num_frames()) / RX.get_sampling_frequency() + 5
    RX2.set_times(times)

    RX3 = se.NumpyRecordingExtractor(timeseries=X, sampling_frequency=sampling_frequency, geom=geom)

    SX = se.NumpySortingExtractor()
    SX.set_sampling_frequency(sampling_frequency)
    spike_times = [200, 300, 400]
    train1 = np.sort(np.rint(np.random.RandomState(seed=seed).uniform(0, num_frames, spike_times[0])).astype(int))
    SX.add_unit(unit_id=1, times=train1)
    SX.add_unit(unit_id=2, times=np.sort(np.random.RandomState(seed=seed).uniform(0, num_frames, spike_times[1])))
    SX.add_unit(unit_id=3, times=np.sort(np.random.RandomState(seed=seed).uniform(0, num_frames, spike_times[2])))
    SX.set_unit_property(unit_id=1, property_name="stability", value=80)
    SX.add_epoch("epoch1", 0, 10)
    SX.add_epoch("epoch2", 10, 20)

    SX2 = se.NumpySortingExtractor()
    SX2.set_sampling_frequency(sampling_frequency)
    spike_times2 = [100, 150, 450]
    train2 = np.rint(np.random.RandomState(seed=seed).uniform(0, num_frames, spike_times2[0])).astype(int)
    SX2.add_unit(unit_id=3, times=train2)
    SX2.add_unit(unit_id=4, times=np.random.RandomState(seed=seed).uniform(0, num_frames, spike_times2[1]))
    SX2.add_unit(unit_id=5, times=np.random.RandomState(seed=seed).uniform(0, num_frames, spike_times2[2]))
    SX2.set_unit_property(unit_id=4, property_name="stability", value=80)
    SX2.set_unit_spike_features(unit_id=3, feature_name="widths", value=np.asarray([3] * spike_times2[0]))
    SX2.copy_epochs(SX)
    SX2.copy_times(RX2)
    for i, unit_id in enumerate(SX2.get_unit_ids()):
        SX2.set_unit_property(unit_id=unit_id, property_name="shared_unit_prop", value=i)
        SX2.set_unit_spike_features(
            unit_id=unit_id, feature_name="shared_unit_feature", value=np.asarray([i] * spike_times2[i])
        )

    SX3 = se.NumpySortingExtractor()
    train3 = np.asarray([1, 20, 21, 35, 38, 45, 46, 47])
    SX3.add_unit(unit_id=0, times=train3)
    features3 = np.asarray([0, 5, 10, 15, 20, 25, 30, 35])
    features4 = np.asarray([0, 10, 20, 30])
    feature4_idx = np.asarray([0, 2, 4, 6])
    SX3.set_unit_spike_features(unit_id=0, feature_name="dummy", value=features3)
    SX3.set_unit_spike_features(unit_id=0, feature_name="dummy2", value=features4, indexes=feature4_idx)

    example_info = dict(
        channel_ids=channel_ids,
        num_channels=num_channels,
        num_frames=num_frames,
        sampling_frequency=sampling_frequency,
        unit_ids=[1, 2, 3],
        train1=train1,
        train2=train2,
        train3=train3,
        features3=features3,
        unit_prop=80,
        channel_prop=(0, 0),
        ttls=ttls,
        epochs_info=((0, 10), (10, 20)),
        geom=geom,
        times=times,
    )

    return (RX, RX2, RX3, SX, SX2, SX3, example_info)
