from nwb_conversion_tools.ophys import SegmentationExtractor2NWBConverter
from segmentationextractors import ExtractSegmentationExtractor
import os
import yaml

class Extract2NWB(SegmentationExtractor2NWBConverter):

    def __init__(self, source_path, nwbfile, metadata):
        if isinstance(source_path, str):
            source_path = [source_path]
        filename = os.path.basename(source_path[0])
        if '.' not in filename:
            raise Exception('provide a *cnmfe*.mat file source')
        if filename.split('.')[-1] not in 'mat' or 'extract' not in filename.split('.')[0]:
            raise Exception('provide a .mat file source')
        self.segext_obj = ExtractSegmentationExtractor(source_path[0])  # source_path=['*\folder.sima']
        super(Extract2NWB, self).__init__(source_path, nwbfile, metadata)


def conversion_function(source_paths=None, f_nwb=None, metadata=None):
    # print(source_paths)
    # print(type(f_nwb))
    # print(len(f_nwb))
    # print(type(metadata))
    print(type(metadata['Ophys']['DfOverF']['roi_response_series'][0]['rate']))
    with open(
            r'C:\Users\Saksham\Google Drive (sxs1790@case.edu)\NWB\nwb-conversion-tools\tests\Ophys\datasets\nct_gui_in.yaml',
            'w') as f:
        yaml.dump(metadata, f)
    if isinstance(f_nwb, str):
        f_nwb = None
    print(list(source_paths.values())[0]['path'], f_nwb, sep='\n\n')