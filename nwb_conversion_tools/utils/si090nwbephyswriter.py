import uuid
from datetime import datetime
import warnings
import numpy as np
import distutils.version
from pathlib import Path
from typing import Union, Optional, List
from distutils.version import StrictVersion
from warnings import warn
import psutil
from collections import defaultdict

import pynwb
from numbers import Real
from hdmf.data_utils import DataChunkIterator
from hdmf.backends.hdf5.h5_utils import H5DataIO
from .json_schema import dict_deep_update
from .basenwbephyswriter import BaseNwbEphysWriter
from .common_writer_tools import ArrayType, PathType, set_dynamic_table_property, check_module, list_get

try:
    import spikeinterface as si

    if StrictVersion(si.__version__) >= StrictVersion("0.90"):
        HAVE_SI_090 = True
    else:
        HAVE_SI_090 = False
except ImportError:
    HAVE_SI_090 = False


class SI090NwbEphysWriter(BaseNwbEphysWriter):
    """
    Class to write a Recording, Sorting, Event, or WaveformExtractor object from SI>=0.90 to NWB

    Parameters
    ----------
    object_to_write: si.BaseRecording, si.BaseSorting, si.BaseEvent, si.WaveformExtractor
    nwb_file_path: Path type
    nwbfile: pynwb.NWBFile or None
    metadata: dict or None
    **kwargs: list kwargs and meaning
    """

    def __init__(
        self,
        object_to_write: Union[si.BaseRecording, si.BaseSorting, si.BaseEvent, si.WaveformExtractor],
        nwb_file_path: PathType = None,
        nwbfile: pynwb.NWBFile = None,
        metadata: dict = None,
        **kwargs,
    ):
        assert HAVE_SI_090
        self.recording, self.sorting, self.waveforms, self.event = None, None, None, None
        BaseNwbEphysWriter.__init__(
            self, object_to_write, nwb_file_path=nwb_file_path, nwbfile=nwbfile, metadata=metadata, **kwargs
        )

    @staticmethod
    def supported_types():
        assert HAVE_SI_090
        return (si.BaseRecording, si.BaseSorting, si.BaseEvent, si.WaveformExtractor)

    def write_to_nwb(self):
        if isinstance(self.object_to_write, si.BaseRecording):
            self.recording = self.object_to_write
            self.write_recording()
        elif isinstance(self.object_to_write, si.BaseRecording):
            self.sorting = self.object_to_write
            self.write_sorting()
        elif isinstance(self.object_to_write, si.BaseEvent):
            self.event = self.object_to_write
            self.write_epochs()
        elif isinstance(self.object_to_write, si.WaveformExtractor):
            self.recording = self.object_to_write.recording
            self.sorting = self.object_to_write.sorting
            self.waveforms = self.object_to_write
            self.write_recording()
            self.write_sorting()
            self.write_waveforms()

    def write_recording(self):
        raise NotImplementedError

    def write_sorting(self):
        raise NotImplementedError

    def write_epochs(self):
        raise NotImplementedError

    def write_waveforms(self):
        raise NotImplementedError

    def get_nwb_metadata(self):
        raise NotImplementedError

    def add_electrodes(self):
        raise NotImplementedError

    def add_electrical_series(self):
        raise NotImplementedError

    def add_units(self):
        raise NotImplementedError

    def add_epochs(self):
        raise NotImplementedError
