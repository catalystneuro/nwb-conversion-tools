"""Collection of modifications of HDMF functions that are to be tested/used on this repo until propagation upstream."""
from typing import Tuple, Optional
from warnings import warn

import numpy as np
from hdmf.data_utils import GenericDataChunkIterator as HDMFGenericDataChunkIterator
from roiextractors import ImagingExtractor


class GenericDataChunkIterator(HDMFGenericDataChunkIterator):
    def _get_default_buffer_shape(self, buffer_gb: float = 1.0) -> Tuple[int]:
        num_axes = len(self.maxshape)
        chunk_bytes = np.prod(self.chunk_shape) * self.dtype.itemsize
        assert buffer_gb > 0, f"buffer_gb ({buffer_gb}) must be greater than zero!"
        assert (
            buffer_gb >= chunk_bytes / 1e9
        ), f"buffer_gb ({buffer_gb}) must be greater than the chunk size ({chunk_bytes / 1e9})!"
        assert all(
            np.array(self.chunk_shape) > 0
        ), f"Some dimensions of chunk_shape ({self.chunk_shape}) are less than zero!"

        maxshape = np.array(self.maxshape)

        # Early termination condition
        if np.prod(maxshape) * self.dtype.itemsize / 1e9 < buffer_gb:
            return tuple(self.maxshape)

        buffer_bytes = chunk_bytes
        axis_sizes_bytes = maxshape * self.dtype.itemsize
        smallest_chunk_axis, second_smallest_chunk_axis, *_ = np.argsort(self.chunk_shape)
        target_buffer_bytes = buffer_gb * 1e9

        # If the smallest full axis does not fit within the buffer size, form a square along the two smallest axes
        sub_square_buffer_shape = np.array(self.chunk_shape)
        if min(axis_sizes_bytes) > target_buffer_bytes:
            k1 = np.floor((target_buffer_bytes / chunk_bytes) ** 0.5)
            for axis in [smallest_chunk_axis, second_smallest_chunk_axis]:
                sub_square_buffer_shape[axis] = k1 * sub_square_buffer_shape[axis]
            return tuple(sub_square_buffer_shape)

        # Original one-shot estimation has good performance for certain shapes
        chunk_to_buffer_ratio = buffer_gb * 1e9 / chunk_bytes
        chunk_scaling_factor = np.floor(chunk_to_buffer_ratio ** (1 / num_axes))
        unpadded_buffer_shape = [
            np.clip(a=int(x), a_min=self.chunk_shape[j], a_max=self.maxshape[j])
            for j, x in enumerate(chunk_scaling_factor * np.array(self.chunk_shape))
        ]

        unpadded_buffer_bytes = np.prod(unpadded_buffer_shape) * self.dtype.itemsize

        # Method that starts by filling the smallest axis completely or calculates best partial fill
        padded_buffer_shape = np.array(self.chunk_shape)
        chunks_per_axis = np.ceil(maxshape / self.chunk_shape)
        small_axis_fill_size = chunk_bytes * min(chunks_per_axis)
        full_axes_used = np.zeros(shape=num_axes, dtype=bool)
        if small_axis_fill_size <= target_buffer_bytes:
            buffer_bytes = small_axis_fill_size
            padded_buffer_shape[smallest_chunk_axis] = self.maxshape[smallest_chunk_axis]
            full_axes_used[smallest_chunk_axis] = True
        for axis, chunks_on_axis in enumerate(chunks_per_axis):
            if full_axes_used[axis]:  # If the smallest axis, skip since already used
                continue
            if chunks_on_axis * buffer_bytes <= target_buffer_bytes:  # If multiple axes can be used together
                buffer_bytes *= chunks_on_axis
                padded_buffer_shape[axis] = self.maxshape[axis]
            else:  # Found an axis that is too large to use with the rest of the buffer; calculate how much can be used
                k3 = np.floor(target_buffer_bytes / buffer_bytes)
                padded_buffer_shape[axis] *= k3
                break
        padded_buffer_bytes = np.prod(padded_buffer_shape) * self.dtype.itemsize

        if padded_buffer_bytes >= unpadded_buffer_bytes:
            return tuple(padded_buffer_shape)
        else:
            return tuple(unpadded_buffer_shape)


class SliceableDataChunkIterator(GenericDataChunkIterator):
    """
    Generic data chunk iterator that works for any memory mapped array, such as a np.memmap or an h5py.Dataset
    """

    def __init__(self, data, **kwargs):
        self.data = data
        super().__init__(**kwargs)

    def _get_dtype(self) -> np.dtype:
        return self.data.dtype

    def _get_maxshape(self) -> tuple:
        return self.data.shape

    def _get_data(self, selection: Tuple[slice]) -> np.ndarray:
        return self.data[selection]


class ImagingExtractorDataChunkIterator(GenericDataChunkIterator):
    """
    Generic data chunk iterator for an ImagingExtractor object
    primarily used when writing imaging data to an NWB file.
    """

    def __init__(
        self,
        imaging_extractor: ImagingExtractor,
        buffer_gb: Optional[float] = None,
        buffer_shape: Optional[tuple] = None,
        chunk_mb: Optional[float] = None,
        chunk_shape: Optional[tuple] = None,
        display_progress: bool = False,
        progress_bar_options: Optional[dict] = None,
    ):
        self.imaging_extractor = imaging_extractor

        assert not (buffer_gb and buffer_shape), "Only one of 'buffer_gb' or 'buffer_shape' can be specified!"
        assert not (chunk_mb and chunk_shape), "Only one of 'chunk_mb' or 'chunk_shape' can be specified!"

        if chunk_mb is None and chunk_shape is None:
            chunk_mb = 1.0

        self._maxshape = self._get_maxshape()
        self._dtype = self._get_dtype()
        if chunk_shape is None:
            chunk_shape = super()._get_default_chunk_shape(chunk_mb=chunk_mb)

        if buffer_gb is None and buffer_shape is None:
            buffer_gb = 1.0

        if buffer_shape is None:
            buffer_shape = self._get_scaled_buffer_shape(buffer_gb=buffer_gb, chunk_shape=chunk_shape)

        super().__init__(
            buffer_shape=buffer_shape,
            chunk_shape=chunk_shape,
            display_progress=display_progress,
            progress_bar_options=progress_bar_options,
        )

    def _get_scaled_buffer_shape(self, buffer_gb: float, chunk_shape: tuple) -> tuple:
        """Select the buffer_shape with size in GB less than the threshold of buffer_gb
        and as a multiplier of chunk_shape."""
        assert buffer_gb > 0, f"buffer_gb ({buffer_gb}) must be greater than zero!"
        assert all(np.array(chunk_shape) > 0), f"Some dimensions of chunk_shape ({chunk_shape}) are less than zero!"
        image_size = self._get_maxshape()[1:]
        min_buffer_shape = tuple([chunk_shape[0]]) + image_size
        scaling_factor = np.floor((buffer_gb * 1e9 / (np.prod(min_buffer_shape) * self._get_dtype().itemsize)))
        max_buffer_shape = tuple([int(scaling_factor * min_buffer_shape[0])]) + image_size
        scaled_buffer_shape = tuple(
            [
                min(max(int(dimension_length), chunk_shape[dimension_index]), self._get_maxshape()[dimension_index])
                for dimension_index, dimension_length in enumerate(max_buffer_shape)
            ]
        )

        return scaled_buffer_shape

    def _get_dtype(self) -> np.dtype:
        return self.imaging_extractor.get_dtype()

    def _get_maxshape(self) -> tuple:
        return (self.imaging_extractor.get_num_frames(),) + self.imaging_extractor.get_image_size()[::-1]

    def _get_data(self, selection: Tuple[slice]) -> np.ndarray:
        data = self.imaging_extractor.get_video(
            start_frame=selection[0].start,
            end_frame=selection[0].stop,
        ).transpose((0, 2, 1))[(slice(0, self.buffer_shape[0]),) + selection[1:]]
        return data
