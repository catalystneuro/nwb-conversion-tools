from ..basedatainterface import BaseDataInterface
from pathlib import Path
from ..nwbconverter import NWBConverter
from ..json_schema_utils import get_base_schema, dict_deep_update
from ..utils import get_schema_from_hdmf_class
import uuid
from datetime import datetime
import pickle
from pynwb import NWBFile, NWBHDF5IO, TimeSeries
from pynwb.file import Subject
from pynwb.behavior import BehavioralTimeSeries

class GiocomoVRInterface(BaseDataInterface):
    """Data interface for VR Pickled data, Giocomo Lab"""

    def __init__(self, file_path: [str, Path]):
        super().__init__()
        self.file_path = Path(file_path)
        assert self.file_path.suffix == '.pkl', 'file_path should be a .pkl'
        assert self.file_path.exists(), 'file_path does not exist'
        with open(self.file_path, 'rb') as pk:
            self.data_frame=pickle.load(pk)['VR_Data']
        self.beh_args = [dict(name='pos',description='(virtual cm) position on virtual reality track',unit='cm'),
                        dict(name='dz',description='(virtual cm) raw rotary encoder information',unit='cm'),
                        dict(name='lick',description='number of licks in 2P frame',unit='n.a.'),
                        dict(name='tstart',description='information about collisions with objects in virtual track, 0-collision',unit='n.a.'),
                        dict(name='teleport',description='information about collisions with objects in virtual track, 0-collision',unit='n.a.'),
                        dict(name='rzone',description='information about collisions with objects in virtual track, 0-collision',unit='n.a.'),
                        dict(name='speed',description='mouse\'s speed on ball',unit='cm/s'),
                        dict(name='lick rate',description='smooth version of no. licks',unit='count/s')]
        self.stimulus_args = [dict(name='morph',description='information about stimulus in arbitrary units',unit='n.a.'),
                             dict(name='towerJitter',description='information about stimulus in arbitrary units',unit='n.a.'),
                             dict(name='wallJitter',description='information about stimulus in arbitrary units',unit='n.a.'),
                             dict(name='bckgndJitter',description='information about stimulus in arbitrary units',unit='n.a.'),
                             dict(name='reward',description='number of rewards dispensed ',unit='n.a.')]

    @classmethod
    def get_source_schema(cls):
        base = super().get_source_schema()
        base.update(required=['file_path'],
                    properties=dict(
                        file_path=dict(
                            type='string')))
        return base

    def get_metadata_schema(self):
        metadata_schema = NWBConverter.get_metadata_schema()
        metadata_schema['required'].append('behavior', 'stimulus')
        metadata_schema['properties']['behavior'] = get_base_schema()
        metadata_schema['properties']['stimulus'] = get_base_schema()
        metadata_schema['properties']['behavior']['properties'] = dict(
            BehavioralTimeSeries=get_schema_from_hdmf_class(BehavioralTimeSeries),
        )

    def get_metadata(self):
        exp_desc = self.file_path.parents[0].name
        date = self.file_path.parents[1].name
        subject_id = self.file_path.parents[2].name
        session_desc = self.file_path.stem
        metadata = dict(
            NWBFile=dict(
                session_description=session_desc,
                identifier=str(uuid.uuid4()),
                session_start_time=datetime.strptime(date, "%m_%d_%Y"),
                experiment_description=exp_desc
            ),
            Subject=dict(
                subject_id=subject_id,
                species="Mus musculus"
            ),
            Behavior=dict(
                time_series=[beh_arg for beh_arg in self.beh_args if beh_arg['name'] in self.data_frame]
            ),
            Stimulus=dict(
                time_series=[stim_arg for stim_arg in self.stimulus_args if stim_arg['name'] in self.data_frame]
            )
        )
        return metadata

    def run_conversion(self, nwbfile: NWBFile, metadata: dict = None, overwrite: bool = False):
        assert isinstance(nwbfile, NWBFile), "'nwbfile' should be of type pynwb.NWBFile"
        metadata_default = self.get_metadata()
        metadata = dict_deep_update(metadata_default, metadata)
        # Subject:
        if nwbfile.subject is None:
            nwbfile.subject = Subject(**metadata['Subject'])
        # adding behavior:
        start_time = 0.0
        rate = 1/self.data_frame.time.diff().mean()
        beh_ts = []
        for behdict in self.beh_args:
            if 'cm' in behdict['unit']:
                conv = 1e-2
                behdict.update(unit='m')
            else:
                conv = 1
            behdict.update(starting_time=start_time, rate=rate, data=self.data_frame[behdict['name']].to_numpy()*conv)
            beh_ts.append(TimeSeries(**behdict))
        if 'behavior' not in nwbfile.processing:
            beh_mod = nwbfile.create_processing_module('behavior', 'Container for behavior time series')
            beh_mod.add(BehavioralTimeSeries(time_series=beh_ts, name='BehavioralTimeSeries'))
        else:
            beh_mod = nwbfile.processing['behavior']
            if 'BehavioralTimeSeries' not in beh_mod.data_interfaces:
                beh_mod.add(BehavioralTimeSeries(time_series=beh_ts, name='BehavioralTimeSeries'))

        # adding stimulus:
        for inp_kwargs in self.stimulus_args:
            if inp_kwargs['name'] not in nwbfile.stimulus:
                inp_kwargs.update(starting_time=start_time, rate=rate, data=self.data_frame[inp_kwargs['name']].to_numpy())
                nwbfile.add_stimulus(TimeSeries(**inp_kwargs))