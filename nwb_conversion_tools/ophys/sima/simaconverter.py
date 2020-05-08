from nwb_conversion_tools.ophys import ProcessedOphysNWBConverter
from segmentationextractors import SimaSegmentationExtractor
from segmentationextractors.nwbsegmentationextractor import iter_datasetvieww
from pynwb.ophys import Fluorescence
from hdmf.data_utils import DataChunkIterator

class Sima2NWB(ProcessedOphysNWBConverter):

    def __init__(self, nwbfile, metadata, source_path):
        #TODO: add channel names from sima instead of default. Or should that be input from gui only? In all other extractors, its none anyway
        if isinstance(source_path,str):
            self.source_paths={'sima_folder': dict(type='folder', path=source_path)}

        self.sima_obj = SimaSegmentationExtractor(source_path['sima_folder']['path'])
        super().__init__(metadata,nwbfile,source_path)
        self.create_plane_segmentation()


    def add_optical_channel(self):
        """
        Metadata is a list of optical channels. Each value in the format of the metafile.schema
        :param metadata:
        :return:
        """
        optical_channel_list = []
        channel_names = self.sima_obj.get_channel_names()
        template_dict = dict(Ophys=dict(OpticalChannel=dict(name='name')))
        for i in channel_names:
            channel_dict = template_dict['Ophys']['OpticalChannel']['name'] = i
            optical_channel_list.append(self.create_optical_channel(channel_dict))
        self.add_imaging_plane(optical_channel=optical_channel_list)

    def add_rois(self):
        for i, roiid in enumerate(self.sima_obj.roi_idx):
            img_roi = self.sima_obj.raw_images[:, :, i]
            self.plane_segmentation.add_roi(image_mask=img_roi)

    def add_fluorescence_traces(self, metadata=None):
        input_kwargs = dict(
            name='RoiResponseSeries',
            description='no description',
            rois=self.create_roi_table_region(self.sima_obj.image_masks.shape[-1]),
            starting_time=0.0,
            rate=self.sima_obj.get_sampling_frequency(),
            unit='lumens'
        )
        if metadata:
            metadata_iter = metadata
        else:
            metadata_iter = self.metadata['Ophys']['DFOverF']['roi_response_series']
        fl = Fluorescence()
        self.ophys_mod.add_data_interface(fl)
        for i in metadata_iter:
            input_kwargs.update(**i)
            input_kwargs.update(
                data=DataChunkIterator(data=iter_datasetvieww(self.sima_obj.roi_response))
            )
            fl.create_roi_response_series(**input_kwargs)

    def create_roi_table_region(self, rois):
        return self.plane_segmentation.create_roi_table_region('NeuronROIs', region=rois)

    def run_conversion(self):
        """
        To populate the nwb file completely.
        :return:
        """
        pass