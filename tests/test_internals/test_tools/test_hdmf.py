import numpy as np
from numpy.testing import assert_array_equal

from nwb_conversion_tools.tools.hdmf import SliceableDataChunkIterator, ImagingExtractorDataChunkIterator

from roiextractors.testing import generate_dummy_imaging_extractor


def test_sliceable_data_chunk_iterator():

    data = np.arange(100).reshape(10, 10)

    dci = SliceableDataChunkIterator(data=data, buffer_shape=(5, 5), chunk_shape=(5, 5))

    data_chunk = next(dci)

    assert data_chunk.selection == (slice(0, 5, None), slice(0, 5, None))

    assert_array_equal(
        data_chunk.data,
        [[0, 1, 2, 3, 4], [10, 11, 12, 13, 14], [20, 21, 22, 23, 24], [30, 31, 32, 33, 34], [40, 41, 42, 43, 44]],
    )


def test_roi_extractors_data_chunk_iterator():
    roi_extractor = generate_dummy_imaging_extractor(num_frames=100)

    dci = ImagingExtractorDataChunkIterator(
        imaging_extractor=roi_extractor,
        buffer_gb=0.00005,
        chunk_mb=0.001,
    )

    data_chunk = next(dci)

    assert data_chunk.selection == (slice(0, 100, None), slice(0, 10, None), slice(0, 10, None))

    assert_array_equal(data_chunk.data, roi_extractor.get_video(start_frame=0, end_frame=100).transpose((0, 2, 1)))
