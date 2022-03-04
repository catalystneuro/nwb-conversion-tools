"""Authors: Saksham Sharda, Cody Baker, Ben Dichter."""
import datetime
import os
import warnings

from ....basedatainterface import BaseDataInterface
from ....tools.nwb_helpers import get_module

try:
    from dlc2nwb.utils import (
        get_movie_timestamps,
        _ensure_individuals_in_header,
        __version__,
        auxiliaryfunctions,
        VideoReader,
        PoseEstimationSeries,
        PoseEstimation,
        pd,
        pickle,
    )

    HAVE_DLC2NWB = True
except ImportError:
    HAVE_DLC2NWB = False


class DeepLabCutInterface(BaseDataInterface):
    """Data interface for DeepLabCut datasets"""

    def __init__(self, dlc_file_path, config_file_path):
        """
        Interface for writing DLC's h5 files to nwb using dlc2nwb.

        Parameters
        ----------
        dlc_file_path: FilePathType
            path to the h5 file output by dlc.
        config_file_path: FilePathType
            path to .yml config file
        """
        if "DLC" not in dlc_file_path or not dlc_file_path.endswith(".h5"):
            raise IOError("The file passed in is not a DeepLabCut h5 data file.")
        assert HAVE_DLC2NWB, "to use this datainterface: 'pip install dlc2nwb'"
        self._config_file = auxiliaryfunctions.read_config(config_file_path)
        super().__init__(dlc_file_path=dlc_file_path, config_file_path=config_file_path)
        self._derived_metadata = self._metadata_from_config()

    def _metadata_from_config(self):
        dlc_file_path = self.source_data["dlc_file_path"]
        vidname, scorer = os.path.split(dlc_file_path)[-1].split("DLC")
        scorer = "DLC" + os.path.splitext(scorer)[0]
        return dict(vidname=vidname, scorer=scorer)

    def get_metadata(self):
        metadata = dict(
            NWBFile=dict(
                session_description=self._config_file["Task"],
                experimenter=self._config_file["scorer"],
                identifier=self._derived_metadata["scorer"],
                session_start_time=datetime.datetime.now(datetime.timezone.utc),
            )
        )
        return metadata

    def run_conversion(self, nwbfile, metadata: dict, individual_name="ind1"):
        """
        Conversion from DLC output files to nwb. Derived from dlc2nwb library.

        Parameters
        ----------
        nwbfile: pynwb.NWBFile
        metadata: dict
        individual_name : str
            Name of the subject (whose pose is predicted) for single-animal DLC project.
            For multi-animal projects, the names from the DLC project will be used directly.

        Returns
        -------
        nwbfile: pynwb.NWBFile
        """
        video = None
        df = _ensure_individuals_in_header(pd.read_hdf(self.source_data["dlc_file_path"]), individual_name)
        # Fetch the corresponding metadata pickle file
        paf_graph = []
        filename, _ = os.path.splitext(self.source_data["dlc_file_path"])
        for i, c in enumerate(filename[::-1]):
            if c.isnumeric():
                break
        if i > 0:
            filename = filename[:-i]
        metadata_file = filename + "_meta.pickle"
        if os.path.isfile(metadata_file):
            with open(metadata_file, "rb") as file:
                metadata = pickle.load(file)
            test_cfg = metadata["data"]["DLC-model-config file"]
            paf_graph = test_cfg.get("partaffinityfield_graph", [])
            if paf_graph:
                paf_inds = test_cfg.get("paf_best")
                if paf_inds is not None:
                    paf_graph = [paf_graph[i] for i in paf_inds]
        else:
            warnings.warn("Metadata not found...")

        for video_path, params in self._config_file["video_sets"].items():
            if self._derived_metadata["vidname"] in video_path:
                video = video_path, params["crop"]
                break

        if video is None:
            warnings.warn(f"The video file corresponding to {self.source_data['dlc_file_path']} could not be found...")
            video = "fake_path", "0, 0, 0, 0"

            timestamps = df.index.tolist()
        else:
            timestamps = get_movie_timestamps(video[0])

        for animal, df_ in df.groupby(level="individuals", axis=1):
            pose_estimation_series = []
            for kpt, xyp in df_.groupby(level="bodyparts", axis=1, sort=False):
                data = xyp.to_numpy()

                pes = PoseEstimationSeries(
                    name=f"{animal}_{kpt}",
                    description=f"Keypoint {kpt} from individual {animal}.",
                    data=data[:, :2],
                    unit="pixels",
                    reference_frame="(0,0) corresponds to the bottom left corner of the video.",
                    timestamps=timestamps,
                    confidence=data[:, 2],
                    confidence_definition="Softmax output of the deep neural network.",
                )
                pose_estimation_series.append(pes)

            pe = PoseEstimation(
                pose_estimation_series=pose_estimation_series,
                description="2D keypoint coordinates estimated using DeepLabCut.",
                original_videos=[video[0]],
                dimensions=[list(map(int, video[1].split(",")))[1::2]],
                scorer=self._derived_metadata["scorer"],
                source_software="DeepLabCut",
                source_software_version=__version__,
                nodes=[pes.name for pes in pose_estimation_series],
                edges=paf_graph,
            )

            get_module(nwbfile=nwbfile, name="behavior", description="processed behavioral data").add(pe)
