from nwb_conversion_tools.ophys import SegmentationExtractor2NWBConverter
from segmentationextractors.schnitzerextractor.extractsegmentationextractor import ExtractSegmentationExtractor
import os
import yaml


class Extract2NWB(SegmentationExtractor2NWBConverter):

    def __init__(self, source_path, nwbfile, metadata):
        if not isinstance(source_path, ExtractSegmentationExtractor):
            if isinstance(source_path, str):
                source_path = [source_path]
            filename = os.path.basename(source_path[0])
            if '.' not in filename:
                raise Exception('provide a *cnmfe*.mat file source')
            if filename.split('.')[-1] not in 'mat' or 'extract' not in filename.split('.')[0]:
                raise Exception('provide a .mat file source')
            self.segext_obj = ExtractSegmentationExtractor(source_path[0])  # source_path=['*\folder.sima']
        else:
            self.segext_obj = source_path
            source_path = self.segext_obj.filepath
        super(Extract2NWB, self).__init__(source_path, nwbfile, metadata)
