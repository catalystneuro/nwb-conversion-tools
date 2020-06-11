from nwb_conversion_tools.ophys import SegmentationExtractor2NWBConverter
from segmentationextractors.schnitzerextractor.cnmfesegmentationextractor import CnmfeSegmentationExtractor
import os
import yaml


class Cnmfe2NWB(SegmentationExtractor2NWBConverter):

    def __init__(self, source_path, nwbfile, metadata):
        segext_obj = CnmfeSegmentationExtractor(source_path)  # source_path=['*\folder.sima']
        super(Cnmfe2NWB, self).__init__(segext_obj, nwbfile, metadata)
