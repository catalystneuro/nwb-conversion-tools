from h5py import File
from pynwb.ophys import Fluorescence
from nwb_conversion_tools.ophys import ProcessedOphysNWBConverter

import numpy as np


class CellMax2NWB(ProcessedOphysNWBConverter):

    def __init__(self, from_path, nwbfile, metadata, add_all=False):
        self.from_path = from_path
        metadata['Ophys']['ImagingPlane'][0]['imaging_rate'] = self.get_frame_rate()
        super(CellMax2NWB, self).__init__(metadata, nwbfile=nwbfile, source_paths=from_path)
        if add_all:
            self.run_conversion()

    def run_conversion(self):
        self.create_plane_segmentation()
        self.ps = self.ps_list[0]
        self.add_img_masks()
        self.add_fluorescence_traces()

    def add_img_masks(self):
        with File(self.from_path, 'r') as f:
            img_masks = f['emAnalysisOutput/cellImages'][:]
        for img_mask in img_masks:
            self.ps.add_roi(image_mask=img_mask)

    def add_fluorescence_traces(self, roi_ids=None, region_label=None):
        if roi_ids is None:
            roi_ids = list(range(len(self.ps)))
            region_label = 'all ROIs'

        rt_region = self.ps.create_roi_table_region(region_label, region=roi_ids)

        frame_rate = self.get_frame_rate()

        with File(self.from_path, 'r') as f:
            data = f['emAnalysisOutput/cellTraces'][:]

        fl = Fluorescence()
        self.ophys_mod.add_data_interface(fl)
        fl.create_roi_response_series('RoiResponseSeries', data, unit='lumens', rois=rt_region, rate=frame_rate)

    def get_frame_rate(self):
        with File(self.from_path, 'r') as f:
            frame_rate = float(f['emAnalysisOutput/eventOptions/framerate'][:])

        return frame_rate







