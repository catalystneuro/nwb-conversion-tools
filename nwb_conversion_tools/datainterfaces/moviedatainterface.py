"""Authors: Cody Baker and Ben Dichter."""
from pathlib import Path
import numpy as np
import psutil
from typing import Optional

from nwb_conversion_tools.basedatainterface import BaseDataInterface
from pynwb import NWBFile
from pynwb.image import ImageSeries
from hdmf.backends.hdf5.h5_utils import H5DataIO
from hdmf.data_utils import DataChunkIterator

from ..conversion_tools import check_regular_timestamps


try:
    import cv2
except ImportError:
    raise ImportError("Please install opencv to use this extractor (pip install opencv-python)!")


class MovieInterface(BaseDataInterface):
    """
    Data interface for writing movies as ImageSeries.

    Source data input argument should be a dictionary with key 'file_paths' and value as an array of PathTypes
    pointing to the video files.
    """

    @classmethod
    def get_source_schema(cls):
        return dict(properties=dict(file_paths=dict(type="array")))

    def run_conversion(
        self,
        nwbfile: NWBFile,
        metadata: dict,
        stub_test: bool = False,
        starting_times: Optional[list] = None,
        chunk_data: bool = False
     ):
        """
        Convert the movie data files to ImageSeries and write them in the NWBFile.

        Parameters
        ----------
        nwbfile : NWBFile
        metadata : dict
        stub_test : bool, optional
            If True, truncates the write operation for fast testing. The default is False.
        starting_times : list, optional
            List of start times for each movie. If unspecified, assumes that the movies in the file_paths list are in
            sequential order and are contiguous.
        chunk_data : bool, optional
            If True, uses a DataChunkIterator to write the movie, reducing overhead RAM usage at the cost of reduced
            conversion speed. This will also force to True whenever the video file size exceeds available system RAM by
            a factor of 4.
        """
        file_paths = self.source_data['file_paths']

        if stub_test:
            count_max = 10
        else:
            count_max = np.inf
        if starting_times is not None:
            assert isinstance(starting_times, list) and all([isinstance(x, float) for x in starting_times]) \
                and len(starting_times) == len(file_paths), \
                "Argument 'starting_times' must be a list of floats in one-to-one correspondence with 'file_paths'!"
        else:
            starting_times = [0.]

        for j, file in enumerate(file_paths):
            cap = cv2.VideoCapture(file)
            if int((cv2.__version__).split('.')[0]) < 3:
                fps = cap.get(cv2.cv.CV_CAP_PROP_FPS)
            else:
                fps = cap.get(cv2.CAP_PROP_FPS)
            n_frames = 0
            timestamps = [starting_times[j] + cap.get(cv2.CAP_PROP_POS_MSEC)]
            success, frame = cap.read()
            while success and n_frames < count_max:
                n_frames += 1
                timestamps.append(starting_times[j] + cap.get(cv2.CAP_PROP_POS_MSEC))
                success, frame = cap.read()
            cap.release()
            if len(starting_times) != len(file_paths):
                starting_times.append(timestamps[-1])

            image_series_kwargs = dict(
                name=f"Video: {Path(file).stem}",
                description="Video recorded by camera.",
                unit="Frames"
            )
            if check_regular_timestamps(timestamps):
                image_series_kwargs.update(starting_time=starting_times[j], rate=fps)
            else:
                image_series_kwargs.update(timestamps=H5DataIO(timestamps, compression="gzip"))

            if chunk_data or Path(file).stat().st_size * 4 > psutil.virtual_memory().available:
                def data_generator(file, count_max):
                    cap = cv2.VideoCapture(file)
                    n_frames = 0
                    success, frame = cap.read()
                    while success and n_frames < count_max:
                        n_frames += 1
                        success, frame = cap.read()
                        yield frame
                    cap.release()
                mov = DataChunkIterator(
                    data=data_generator(file=file, count_max=count_max),
                    iter_axis=0,  # nwb standard is time as zero axis
                    # maxshape=(recording.get_num_frames(), recording.get_num_channels())
                )
                image_series_kwargs.update(data=H5DataIO(mov, compression="gzip"))
            else:
                cap = cv2.VideoCapture(file)
                mov = []
                n_frames = 0
                success, frame = cap.read()
                while success and n_frames < count_max:
                    mov.append(frame)
                    n_frames += 1
                    success, frame = cap.read()
                cap.release()
                image_series_kwargs.update(data=H5DataIO(np.array(mov), compression="gzip"))
            nwbfile.add_acquisition(ImageSeries(**image_series_kwargs))
