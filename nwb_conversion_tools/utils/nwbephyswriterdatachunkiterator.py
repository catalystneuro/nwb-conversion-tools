"""Authors: Saksham Sharda, Alessio Buccino."""
import numpy as np
from typing import Tuple, Iterable, Union
from distutils.version import StrictVersion

from .genericdatachunkiterator import GenericDataChunkIterator

from .basenwbephyswriter import BaseNwbEphysWriter


class NwbEphysWriterDataChunkIterator(GenericDataChunkIterator):
    """DataChunkIterator for use on RecordingExtractor (spikeinterface/spikeinterface) objects."""

    def __init__(
        self,
        ephys_writer: BaseNwbEphysWriter,
        segment_index: int = 0,
        unsigned_coercion: list = None,
        write_scaled: bool = False,
        buffer_gb: float = None,
        buffer_shape: tuple = None,
        chunk_mb: float = None,
        chunk_shape: tuple = None,
        dtype: Union[str, np.dtype] = None
    ):
        """
        Initialize an Iterable object which returns DataChunks with data and their selections on each iteration.

        Parameters
        ----------
        ephys_writer : BaseNwbEphysWriter
          The BaseNwbEphysWriter object which handles the API for data transfer.
        segment_index : int, optional
          The segment to iterate on (if multi-segment object). The default is 0.
        unsigned_coercion : list, optional
          For unsigned data types (e.g., uint16), this value shifts the dtype to a signed type.
          The default is None.
        write_scaled : bool, optional
          Whether to scale the data by the internal conversion factor ('gain', in spikeinterface).
          The default is True.
        buffer_gb : float, optional
          The upper bound on size in gigabytes (GB) of each selection from the iteration.
          The buffer_shape will be set implicitly by this argument.
          The default is 1GB.
        buffer_shape : tuple, optional
          If the user desires further control over the shaping of the buffer over all the axes,
          they may set this explicitly as a tuple of the same length as the data shape indicating the desired shape
          of each selection.
          The default is None.
        chunk_mb : float, optional
          The upper bound on size in megabytes (MB) of each internally set chunk for the HDF5 dataset.
          The chunk_shape will be set implicitly by this argument.
          The default is 1MB, which is highly recommended by the HDF5 group. For more details, see
          https://support.hdfgroup.org/HDF5/doc/TechNotes/TechNote-HDF5-ImprovingIOPerformanceCompressedDatasets.pdf
        chunk_shape : tuple, optional
          If the user desires further control over the shaping of the buffer over all the axes,
          they may set this explicitly as a tuple of the same length as the data shape indicating the desired shape
          of each selection.
          The default is None.
        """
        self.segment_index = segment_index
        self.write_scaled = write_scaled
        self.ephys_writer = ephys_writer
        self.channel_ids = list(ephys_writer.recording.get_channel_ids())
        self.unsigned_coercion = (
            np.zeros(shape=(len(self.channel_ids)), dtype=int)
            if unsigned_coercion is None
            else np.array(unsigned_coercion).astype(int)
        )
        self._dtype = np.dtype(dtype)
        super().__init__(buffer_gb=buffer_gb, buffer_shape=buffer_shape, chunk_mb=chunk_mb, chunk_shape=chunk_shape)

    def _get_data(self, selection: Tuple[slice]) -> Iterable:
        channel_ids = self.channel_ids[selection[1]]
        channel_idxs = np.array([self.channel_ids.index(ch) for ch in channel_ids], dtype="int")
        
        data = self.ephys_writer._get_traces(
            channel_ids=channel_ids,
            start_frame=selection[0].start,
            end_frame=selection[0].stop,
            return_scaled=self.write_scaled,
            segment_index=self.segment_index,
        )
        
        if self.dtype is not None:
            data = data.astype(self.dtype)

        data = data + self.unsigned_coercion[channel_idxs]
        return data

    def _get_dtype(self):
        if self._dtype is None:
            return self.ephys_writer._get_dtype(self.write_scaled)
        else:
            return self._dtype

    def _get_maxshape(self):
        return (self.ephys_writer._get_num_frames(self.segment_index), len(self.ephys_writer._get_channel_ids()))
