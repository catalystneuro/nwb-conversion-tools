from nwb_conversion_tools.ophys import SegmentationExtractor2NWBConverter
from segmentationextractors.suite2p.suite2psegmentationextractor import Suite2pSegmentationExtractor
import yaml
import os


class Suite2p2NWB(SegmentationExtractor2NWBConverter):

    def __init__(self, source_path, nwbfile, metadata):
        if not isinstance(source_path,Suite2pSegmentationExtractor):
            if isinstance(source_path, str):
                source_path = [source_path]
            filename = os.path.basename(source_path[0])
            if 'suite2p' not in filename:
                raise Exception('provide a \'suite2p\' folder source')
            self.segext_obj = Suite2pSegmentationExtractor(source_path[0])
        else:
            self.segext_obj = source_path
            source_path = self.segext_obj.filepath
        # source_path=['*\folder.sima']
        roi_resp_dict=dict()
        name_strs = ['Fluorescence', 'Neuropil', 'Deconvolved']
        for i in name_strs:
            roi_resp_dict[i]=self.segext_obj.get_traces(name=i)
        self.segext_obj.roi_response = roi_resp_dict
        super(Suite2p2NWB, self).__init__(source_path, nwbfile, metadata)

def conversion_function(source_paths=None, f_nwb=None, metadata=None):
    if isinstance(f_nwb, str):
        f_nwb = None
    nwbloc =  r'C:\Users\Saksham\Google Drive (sxs1790@case.edu)\NWB\nwb-conversion-tools\tests\Ophys\datasets\test_nwb_suite2p_gui.nwb'
    fileloc = list(source_paths.values())[0]['path']
    obj = Suite2p2NWB(fileloc, None, metadata)

    obj.run_conversion()

    obj.save(nwbloc)
    return obj.nwbfile
