from nwb_conversion_tools.ophys import SegmentationExtractor2NWBConverter
from segmentationextractors.suite2p.suite2psegmentationextractor import Suite2pSegmentationExtractor
import yaml
import os


class Suite2p2NWB(SegmentationExtractor2NWBConverter):

    def __init__(self, source_path, nwbfile, metadata):
        seg_obj = Suite2pSegmentationExtractor(source_path)
        super(Suite2p2NWB, self).__init__(seg_obj, nwbfile, metadata)
