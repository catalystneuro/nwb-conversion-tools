from nwb_conversion_tools.ophys import SegmentationExtractor2NWBConverter
from segmentationextractors.schnitzerextractor.extractsegmentationextractor import ExtractSegmentationExtractor
import os
import yaml


class Extract2NWB(SegmentationExtractor2NWBConverter):

    def __init__(self, source_path, nwbfile, metadata):
        segext_obj = ExtractSegmentationExtractor(source_path)  # source_path=['*\folder.sima']
        super(Extract2NWB, self).__init__(segext_obj, nwbfile, metadata)
