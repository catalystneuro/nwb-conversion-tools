import numpy as np
from numpy.testing import assert_array_equal
from parameterized import parameterized, param

from hdmf.testing import TestCase
from nwbinspector.utils import get_package_version
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


def custom_name_func(testcase_func, param_num, param):
    return f"{testcase_func.__name__}_{param_num}" f"_{param.kwargs.get('case_name', '')}"


class TestImagingExtractorDataChunkIterator(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.imaging_extractor = generate_dummy_imaging_extractor()

    iterator_params = [
        param(
            buffer_gb=1,
            buffer_shape=(10, 10, 10),
            expected_error_msg="Only one of 'buffer_gb' or 'buffer_shape' can be specified!",
            case_name="buffer_gb_and_buffer_shape",
        ),
        param(
            chunk_mb=1,
            chunk_shape=(5, 5, 5),
            expected_error_msg="Only one of 'chunk_mb' or 'chunk_shape' can be specified!",
            case_name="chunk_mb_and_chunk_shape",
        ),
        param(
            buffer_gb=0.0001,
            chunk_mb=1,
            expected_error_msg="chunk_mb must be less than or equal to buffer_gb!",
            case_name="chunk_mb_greater_than_buffer_gb",
        ),
        param(
            buffer_gb=0,
            expected_error_msg="buffer_gb (0) must be greater than zero!",
            case_name="buffer_gb_zero",
        ),
        param(
            chunk_mb=0,
            expected_error_msg="chunk_mb (0) must be greater than zero!",
            case_name="chunk_mb_zero",
        ),
        param(
            buffer_shape=(0, 10, 10),
            expected_error_msg=f"Some dimensions of buffer_shape ((0, 10, 10)) are less than zero!",
            case_name="buffer_shape_less_than_zero",
        ),
        param(
            chunk_shape=(0, 10, 10),
            expected_error_msg=f"Some dimensions of chunk_shape ((0, 10, 10)) are less than zero!",
            case_name="chunk_shape_less_than_zero",
        ),
        param(
            buffer_shape=(5, 10, 10),
            chunk_shape=(2, 2, 2),
            expected_error_msg="Some dimensions of chunk_shape ((2, 2, 2)) do not evenly divide the buffer shape ((5, 10, 10))!",
            case_name="buffer_shape_not_divisible_by_chunk_shape",
        ),
    ]

    param_chunk_shape_exceeds_buffer_shape = param(
        buffer_shape=(5, 10, 10),
        chunk_shape=(13, 2, 2),
        case_name="chunk_shape_greater_than_buffer_shape",
    )
    if get_package_version(name="hdmf").base_version >= "3.3.2":
        param_chunk_shape_exceeds_buffer_shape.kwargs[
            "expected_error_msg"
        ] = "Some dimensions of chunk_shape ((13, 2, 2)) exceed the buffer shape ((5, 10, 10))!"
    else:
        param_chunk_shape_exceeds_buffer_shape.kwargs[
            "expected_error_msg"
        ] = "Some dimensions of chunk_shape ((13, 2, 2)) exceed the manual buffer shape ((5, 10, 10))!"

    iterator_params.append(param_chunk_shape_exceeds_buffer_shape)

    @parameterized.expand(
        input=iterator_params,
        name_func=custom_name_func,
    )
    def test_iterator_assertions(
        self,
        buffer_gb: float = None,
        buffer_shape: tuple[int, int, int] = None,
        chunk_mb: float = None,
        chunk_shape: tuple[int, int, int] = None,
        expected_error_msg: str = None,
        case_name="",
    ):
        """Test that the iterator raises the expected error when the assertions are violated."""
        with self.assertRaisesWith(
            AssertionError,
            exc_msg=expected_error_msg,
        ):
            ImagingExtractorDataChunkIterator(
                imaging_extractor=self.imaging_extractor,
                buffer_gb=buffer_gb,
                buffer_shape=buffer_shape,
                chunk_mb=chunk_mb,
                chunk_shape=chunk_shape,
            )

    @parameterized.expand(
        input=[
            param(
                case_name="with_default_buffer_shape_and_chunk_shape",
            ),
            param(
                max_data_shape=(28, 10, 10),
                buffer_shape=(9, 10, 10),
                chunk_shape=(3, 10, 10),
                case_name="with_custom_buffer_shape_and_chunk_shape",
            ),
            param(
                max_data_shape=(27, 10, 10),
                buffer_shape=(10, 5, 5),
                chunk_shape=(5, 5, 5),
                case_name="with_custom_buffer_shape_and_chunk_shape",
            ),
            param(
                max_data_shape=(1000, 300, 200),
                buffer_gb=0.1,
                case_name="with_custom_buffer_gb_large_data_shape",
            ),
            param(
                max_data_shape=(1000, 300, 200),
                buffer_gb=0.01,
                chunk_mb=0.01,
                case_name="with_custom_buffer_gb_large_data_shape",
            ),
        ],
        name_func=custom_name_func,
    )
    def test_data_validity(
        self,
        max_data_shape: tuple[int, int, int] = None,
        buffer_gb: float = None,
        buffer_shape: tuple[int, int, int] = None,
        chunk_mb: float = None,
        chunk_shape: tuple[int, int, int] = None,
        case_name="",
    ):
        """Test that the iterator returns the expected data given different buffer and chunk shapes."""
        if max_data_shape is None:
            imaging_extractor = self.imaging_extractor
        else:
            imaging_extractor = generate_dummy_imaging_extractor(
                num_frames=max_data_shape[0],
                num_columns=max_data_shape[1],
                num_rows=max_data_shape[2],
            )

        dci = ImagingExtractorDataChunkIterator(
            imaging_extractor=imaging_extractor,
            buffer_gb=buffer_gb,
            buffer_shape=buffer_shape,
            chunk_mb=chunk_mb,
            chunk_shape=chunk_shape,
        )

        if buffer_gb is not None:
            assert ((np.prod(dci.buffer_shape) * self.imaging_extractor.get_dtype().itemsize) / 1e9) <= buffer_gb

        data_chunks = np.zeros(dci.maxshape)
        for data_chunk in dci:
            data_chunks[data_chunk.selection] = data_chunk.data

        expected_frames = imaging_extractor.get_video().transpose((0, 2, 1))
        assert_array_equal(data_chunks, expected_frames)
