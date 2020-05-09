from nwb_conversion_tools.ophys import ProcessedOphysNWBConverter
from segmentationextractors import SimaSegmentationExtractor
from segmentationextractors.nwbextractor.nwbsegmentationextractor import iter_datasetvieww
from pynwb.ophys import Fluorescence, TwoPhotonSeries
from hdmf.data_utils import DataChunkIterator
import yaml
from datetime import datetime

class Sima2NWB(ProcessedOphysNWBConverter):

    def __init__(self, source_path, nwbfile, metadata):
        #TODO: add channel names from sima instead of default. Or should that be input from gui only? In all other extractors, its none anyway
        if isinstance(source_path,str):
            self.source_paths={'sima_folder': dict(type='folder', path=source_path)}
        else:
            self.source_paths=source_path
        if isinstance(metadata,str):
            with open(metadata,'r') as f:
                metadata = yaml.safe_load(f)
        source_path_folder = list(self.source_paths.keys())[0]
        self.sima_obj = SimaSegmentationExtractor(self.source_paths[source_path_folder]['path'])
        super().__init__(metadata,nwbfile,source_path)
        self.auto_create_dict = dict(imaging_plane=False,
                                     two_photon_series=True,
                                     plane_segmentation=True)

    def create_two_photon_series(self, metadata=None, imaging_plane=None):
        if imaging_plane is None:
            if self.nwbfile.imaging_planes:
                imaging_plane = self.nwbfile.imaging_planes[list(self.nwbfile.imaging_planes.keys())[0]]
            else:
                imaging_plane = self.add_imaging_plane()

        input_kwargs = dict(
            name='TwoPhotonSeries',
            description='no description',
            external_file=[self.sima_obj.get_movie_location()],
            format='external',
            rate=self.sima_obj.get_sampling_frequency(),
            starting_time=0.0,
            imaging_plane=imaging_plane,
            starting_frame=[0]
        )

        if metadata is None and 'Ophys' in self.metadata and 'TwoPhotonSeries' in self.metadata['Ophys']:
            metadata = self.metadata['Ophys']['TwoPhotonSeries']
        if metadata:
            input_kwargs.update(metadata)

        return self.nwbfile.add_acquisition(TwoPhotonSeries(**input_kwargs))

    def create_imaging_plane(self, optical_channel_list=None):
        """
        :param optical_channel_list:
        :return:
        """
        if not optical_channel_list:
            optical_channel_list = []
        channel_names = self.sima_obj.get_channel_names()
        template_dict = dict(name='name')
        for i in channel_names:
            template_dict['name'] = i
            optical_channel_list.append(self.create_optical_channel(template_dict))
        self.imaging_plane = self.add_imaging_plane(optical_channel=optical_channel_list)

    def add_rois(self):
        for i, roiid in enumerate(self.sima_obj.roi_idx):
            img_roi = self.sima_obj.raw_images[:, :, i]
            self.plane_segmentation.add_roi(image_mask=img_roi)

    def add_fluorescence_traces(self, metadata=None):
        input_kwargs = dict(
            name='RoiResponseSeries',
            description='no description',
            rois=self.create_roi_table_region(list(range(self.sima_obj.image_masks.shape[-1]))),
            starting_time=0.0,
            rate=self.sima_obj.get_sampling_frequency(),
            unit='lumens'
        )
        if metadata:
            metadata_iter = metadata
        else:
            metadata_iter = self.metadata['Ophys']['DFOverF']['roi_response_series']
            metadata_iter[0].update(
                {'rois':self.create_roi_table_region(list(range(self.sima_obj.image_masks.shape[-1])))})
        fl = Fluorescence()
        self.ophys_mod.add_data_interface(fl)
        for i in metadata_iter:
            input_kwargs.update(**i)
            input_kwargs.update(
                data=DataChunkIterator(data=iter_datasetvieww(self.sima_obj.roi_response))
            )
            fl.create_roi_response_series(**input_kwargs)

    def create_roi_table_region(self, rois, region_name= 'NeuronROIs'):
        return self.plane_segmentation.create_roi_table_region(region_name, region=rois)

    def run_conversion(self):
        """
        To populate the nwb file completely.
        :return:
        """
        self.create_imaging_plane()
        self.create_plane_segmentation()
        self.add_rois()
        self.add_fluorescence_traces()
        self.create_two_photon_series(imaging_plane=self.nwbfile.get_imaging_plane(name='ImagingPlane'))