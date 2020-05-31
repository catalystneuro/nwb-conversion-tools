from nwb_conversion_tools.ophys import SegmentationExtractor2NWBConverter
from segmentationextractors import CnmfeSegmentationExtractor
import os
import yaml


class Cnmfe2NWB(SegmentationExtractor2NWBConverter):

    def __init__(self, source_path, nwbfile, metadata):
        if isinstance(source_path, str):
            source_path = [source_path]
        filename = os.path.basename(source_path[0])
        if '.' not in filename:
            raise Exception('provide a *cnmfe*.mat file source')
        if filename.split('.')[-1] not in 'mat' or 'cnmfe' not in filename.split('.')[0]:
            raise Exception('provide a *cnmfe*.mat file source')
        self.segext_obj = CnmfeSegmentationExtractor(source_path[0])  # source_path=['*\folder.sima']
        super(Cnmfe2NWB, self).__init__(source_path, nwbfile, metadata)

def conversion_function(source_paths=None, f_nwb=None, metadata=None):
    if isinstance(f_nwb, str):
        f_nwb = None
    nwbloc =  r'C:\Users\Saksham\Google Drive (sxs1790@case.edu)\NWB\nwb-conversion-tools\tests\Ophys\datasets\test_nwb_cnmfe_gui.nwb'
    fileloc = list(source_paths.values())[0]['path']
    obj = Cnmfe2NWB(fileloc, None, metadata)

    obj.run_conversion()

    obj.save(nwbloc)
    return obj.nwbfile