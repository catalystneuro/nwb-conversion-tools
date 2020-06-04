from nwb_conversion_tools.ophys import SegmentationExtractor2NWBConverter
from segmentationextractors import SimaSegmentationExtractor
import yaml
import os


class Sima2NWB(SegmentationExtractor2NWBConverter):

    def __init__(self, source_path, nwbfile, metadata):
        if isinstance(source_path, str):
            source_path = [source_path]
        filename = os.path.basename(source_path[0])
        if filename.split('.')[-1] not in 'sima':
            raise Exception('provide a *.sima file source')
        self.segext_obj = SimaSegmentationExtractor(source_path[0])  # source_path=['*\folder.sima']
        super(Sima2NWB, self).__init__(source_path, nwbfile, metadata)

