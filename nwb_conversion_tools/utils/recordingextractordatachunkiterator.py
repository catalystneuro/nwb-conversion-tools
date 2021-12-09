"""Authors: Cody Baker and Saksham Sharda."""
from typing import Tuple, Iterable

from .genericdatachunkiterator import GenericDataChunkIterator

try:
    from spikeextractors import RecordingExtractor

    HAVE_SI013 = True
except ImportError:
    HAVE_SI013 = False


class RecordingExtractorDataChunkIterator(GenericDataChunkIterator):
    """DataChunkIterator for use on RecordingExtractor (from legacy spikeinterface/spikeextractors) objects."""

    def __init__(
        self,
        recording: RecordingExtractor,
        buffer_gb: float = None,
        buffer_shape: Tuple[int] = None,
        chunk_mb: float = None,
        chunk_shape: Tuple[int] = None,
    ):
        """
        Initialize an Iterable object which returns DataChunks with data and their selections on each iteration.

        Parameters
        ----------
        recording : RecordingExtractor
            The RecordingExtractor object (from legacy spikeinterface/spikeextractors)
            which handles the API for data transfer.
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
        assert HAVE_SI013, "spikeextractors v0.13 is not installed (pip install spikeextractors)!"
        self.recording = recording
        self.channel_ids = recording.get_channel_ids()
        super().__init__(buffer_gb=buffer_gb, buffer_shape=buffer_shape, chunk_mb=chunk_mb, chunk_shape=chunk_shape)

    def _get_data(self, selection: Tuple[slice]) -> Iterable:
        return self.recording.get_traces(
            channel_ids=self.channel_ids[selection[1]],
            start_frame=selection[0].start,
            end_frame=selection[0].stop,
            return_scaled=False,
        ).T

    def _get_dtype(self):
        return self.recording.get_dtype(return_scaled=False)

    def _get_maxshape(self):
        return (self.recording.get_num_frames(), self.recording.get_num_channels())
