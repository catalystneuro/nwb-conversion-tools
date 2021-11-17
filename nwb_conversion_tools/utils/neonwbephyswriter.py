from abc import abstractmethod
from distutils.version import StrictVersion

import pynwb

from .basenwbephyswriter import BaseNwbEphysWriter

try:
    import neo

    if StrictVersion(neo.__version__) >= StrictVersion("0.10"):
        HAVE_NEO = True
    else:
        HAVE_NEO = False
except ImportError:
    HAVE_NEO = False


class NEONwbEphysWriter(BaseNwbEphysWriter):
    """
    Class to write a neo.RawIO or neo.IO versio>=0.10 to NWB

    Parameters
    ----------
    object_to_write: neo.RawIO or neo.IO
    stub: bool
        whether to write a subset of recording extractor traces array as electrical series in nwbfile
    stub_channels: list
        channels to include when writing as stub
    """

    def __init__(self, object_to_write, stub=False, stub_channels=None):
        assert HAVE_NEO
        self.recording, self.sorting, self.event = None, None, None
        BaseNwbEphysWriter.__init__(self, object_to_write, stub=stub, stub_channels=stub_channels)

    @staticmethod
    def supported_types():
        assert HAVE_NEO
        return (neo.rawio.baserawio.BaseRawIO, neo.io.baseio.BaseIO)

    def add_to_nwb(self, nwbfile: pynwb.NWBFile, metadata=None, **kwargs):
        # check what's in the neo object: analogsignals, spike trains, events and
        # write recording, sorting, events accordingly
        raise NotImplementedError

    def add_recording(self, segment_index=0):
        raise NotImplementedError

    def add_sorting(self):
        raise NotImplementedError

    def add_waveforms(self):
        raise NotImplementedError

    def add_epochs(self):
        raise NotImplementedError

    def _make_recording_stub(self):
        raise NotImplementedError

    def _make_sorting_stub(self):
        raise NotImplementedError

    def _get_sampling_frequency(self):
        pass

    def _get_channel_ids(self):
        pass

    def _get_unit_sampling_frequency(self):
        pass

    def _get_unit_ids(self):
        pass

    def _get_traces(self, channel_ids=None, start_frame=None, end_frame=None, return_scaled=True, segment_index=0):
        pass

    def _get_dtype(self, return_scaled=True):
        pass

    def _get_channel_property_names(self):
        pass

    def _get_channel_property_values(self, prop):
        pass

    def _get_num_frames(self, segment_index=0):
        pass

    def _get_recording_times(self, segment_index=0):
        pass

    def _get_unit_spike_train_ids(self, unit_id, start_frame=None, end_frame=None, segment_index=None):
        pass

    def _get_unit_spike_train_times(self, unit_id, segment_index=0):
        pass

    def _get_unit_property_names(self):
        pass

    def _get_unit_property_values(self, prop):
        pass

    def _get_unit_waveforms_templates(self, unit_id, mode="mean"):
        pass