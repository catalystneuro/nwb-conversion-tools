"""Authors: Cody Baker and Ben Dichter."""
from pathlib import Path
import numpy as np

from nwb_conversion_tools.basedatainterface import BaseDataInterface
from pynwb import NWBFile
from pynwb.image import ImageSeries
from hdmf.backends.hdf5.h5_utils import H5DataIO


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

    def __init__(self, **source_data):
        super().__init__(**source_data)
        self.starting_times = [0.]

    def run_conversion(
        self,
        nwbfile: NWBFile,
        metadata: dict,
        stub_test: bool = False,
        starting_times: list = None
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
        """
        file_paths = self.source_data['file_paths']

        if stub_test:
            count_max = 10
        else:
            count_max = np.inf
        if starting_times is not None:
            assert isinstance(starting_times, list) and all([isinstance(x, float) for x in starting_times]) \
                and len(starting_times) == len(file_paths), "Argument 'starting_times' must be a list of floats!"
            self.starting_times = starting_times

        for j, file in enumerate(file_paths):
            cap = cv2.VideoCapture(file)
            if int((cv2.__version__).split('.')[0]) < 3:
                fps = cap.get(cv2.cv.CV_CAP_PROP_FPS)
            else:
                fps = cap.get(cv2.CAP_PROP_FPS)

            mov = []
            n_frames = 0
            success, frame = cap.read()
            while success and n_frames < count_max:
                mov.append(frame)
                n_frames += 1
                success, frame = cap.read()
            mov = np.array(mov)
            cap.release()

            video = ImageSeries(
                name=f"Video: {Path(file).stem}",
                description="Video recorded by camera.",
                data=H5DataIO(mov, compression="gzip"),
                starting_time=self.starting_times[j],
                rate=fps,
                unit='Frames'
            )
            if starting_times is None:
                self.starting_times.append((n_frames+1) / fps)
            nwbfile.add_acquisition(video)
