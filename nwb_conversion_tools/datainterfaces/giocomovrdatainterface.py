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
        subject_num = self.file_path.parents[2].name
        session_desc = self.file_path.stem
        subject_details = subject_info[subject_num]
        metadata = dict(
            NWBFile=dict(
                session_description=session_desc,
                identifier=str(uuid.uuid4()),
                session_start_time=datetime.strptime(date, "%m_%d_%Y"),
                experiment_description=exp_desc
            ),
            Subject=dict(
                subject_id=subject_details['ID'],
                species=subject_details['species'],
                date_of_birth=subject_details['DOB'],
                genotype=subject_details['genotype'],
                sex=subject_details['sex'],
                weight=subject_details['weight at time of implant'],
                description=f'virus injection date: {subject_details["virus injection date"]}, \
                            virus: {subject_details["VIRUS"]},\
                            cannula implant date: {subject_details["cannula implant date"]}'
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


subject_info = \
    {'4139265.3': {'mouse #': '4139265.3', 'species': 'mus musculus', 'ID': 'R1', 'DOB': '2018-11-07 00:00:00',
                   'genotype': 'CaMKII-cre hemizygous', 'sex': 'MALE', 'virus injection date': '2018-12-20 00:00:00',
                   'VIRUS': 'AAV-PHP.eB-EF1a-DIO-GCaMP6f (retro-orbital injection)',
                   'cannula implant date': '2019-01-09 00:00:00', 'weight at time of implant': '24.1 g'},
     '4139265.4': {'mouse #': '4139265.4', 'species': 'mus musculus', 'ID': 'R2', 'DOB': '2018-11-07 00:00:00',
                   'genotype': 'CaMKII-cre hemizygous', 'sex': 'MALE', 'virus injection date': '2018-12-20 00:00:00',
                   'VIRUS': 'AAV-PHP.eB-EF1a-DIO-GCaMP6f (retro-orbital injection)',
                   'cannula implant date': '2019-01-09 00:00:00', 'weight at time of implant': '23.0 g'},
     '4139265.5': {'mouse #': '4139265.5', 'species': 'mus musculus', 'ID': 'R3', 'DOB': '2018-11-07 00:00:00',
                   'genotype': 'CaMKII-cre hemizygous', 'sex': 'MALE', 'virus injection date': '2018-12-20 00:00:00',
                   'VIRUS': 'AAV-PHP.eB-EF1a-DIO-GCaMP6f (retro-orbital injection)',
                   'cannula implant date': '2019-01-09 00:00:00', 'weight at time of implant': '22.9 g'},
     '4222168.1': {'mouse #': '4222168.1', 'species': 'mus musculus', 'ID': 'R4', 'DOB': '2019-03-03 00:00:00',
                   'genotype': 'CaMKII-cre hemizygous', 'sex': 'FEMALE', 'virus injection date': '2019-07-17 00:00:00',
                   'VIRUS': 'AAV1-CAG-FLEX-GCaMP6f-WPRE', 'cannula implant date': '2019-07-17 00:00:00',
                   'weight at time of implant': '18.6 g'},
     '4343703.1': {'mouse #': '4343703.1', 'species': 'mus musculus', 'ID': 'R5', 'DOB': '2019-10-29 00:00:00',
                   'genotype': 'CaMKII-cre hemizygous', 'sex': 'MALE', 'virus injection date': '2020-02-20 00:00:00',
                   'VIRUS': 'AAV1-CAG-FLEX-GCaMP6f-WPRE', 'cannula implant date': '2020-02-20 00:00:00',
                   'weight at time of implant': '29.8 g'},
     '4343706.0': {'mouse #': '4343706.0', 'species': 'mus musculus', 'ID': 'R6', 'DOB': '2019-12-19 00:00:00',
                   'genotype': 'WT', 'sex': 'MALE', 'virus injection date': '2019-12-19 00:00:00',
                   'VIRUS': 'AAV1-syn-jGCaMP7f-WPRE', 'cannula implant date': '2020-12-19 00:00:00',
                   'weight at time of implant': '26.6 g'},
     '4222153.1': {'mouse #': '4222153.1', 'species': 'mus musculus', 'ID': 'F1', 'DOB': '2019-01-17 00:00:00',
                   'genotype': 'CaMKII-cre hemizygous', 'sex': 'MALE', 'virus injection date': '2019-03-14 00:00:00',
                   'VIRUS': 'AAV1-CAG-FLEX-GCaMP6f-WPRE', 'cannula implant date': '2019-03-14 00:00:00',
                   'weight at time of implant': '28.8 g'},
     '4222153.2': {'mouse #': '4222153.2', 'species': 'mus musculus', 'ID': 'F2', 'DOB': '2019-01-17 00:00:00',
                   'genotype': 'CaMKII-cre hemizygous', 'sex': 'MALE', 'virus injection date': '2019-03-14 00:00:00',
                   'VIRUS': 'AAV1-CAG-FLEX-GCaMP6f-WPRE', 'cannula implant date': '2019-03-14 00:00:00',
                   'weight at time of implant': '29.3 g'},
     '4222153.3': {'mouse #': '4222153.3', 'species': 'mus musculus', 'ID': 'F3', 'DOB': '2019-01-17 00:00:00',
                   'genotype': 'CaMKII-cre hemizygous', 'sex': 'MALE', 'virus injection date': '2019-03-14 00:00:00',
                   'VIRUS': 'AAV1-CAG-FLEX-GCaMP6f-WPRE', 'cannula implant date': '2019-03-14 00:00:00',
                   'weight at time of implant': '28.0 g'},
     '4222174.1': {'mouse #': '4222174.1', 'species': 'mus musculus', 'ID': 'F4', 'DOB': '2018-10-29 00:00:00',
                   'genotype': 'Ai94 hemizygous; CaMKII-cre hemizygous; CaMKII-tTA hemizygous', 'sex': 'FEMALE',
                   'virus injection date': '2019-04-13 00:00:00', 'VIRUS': 'NONE',
                   'cannula implant date': '2019-04-13 00:00:00', 'weight at time of implant': '23.1 g'},
     '4222154.1': {'mouse #': '4222154.1', 'species': 'mus musculus', 'ID': 'F5', 'DOB': '2019-01-07 00:00:00',
                   'genotype': 'CaMKII-cre hemizygous', 'sex': 'FEMALE', 'virus injection date': '2019-03-13 00:00:00',
                   'VIRUS': 'AAV1-CAG-FLEX-GCaMP6f-WPRE', 'cannula implant date': '2019-03-13 00:00:00',
                   'weight at time of implant': '21.4 g'},
     '4343702.1': {'mouse #': '4343702.1', 'species': 'mus musculus', 'ID': 'F6', 'DOB': '2019-10-29 00:00:00',
                   'genotype': 'CaMKII-cre hemizygous', 'sex': 'FEMALE', 'virus injection date': '2020-02-20 00:00:00',
                   'VIRUS': 'AAV1-CAG-FLEX-GCaMP6f-WPRE', 'cannula implant date': '2020-02-20 00:00:00',
                   'weight at time of implant': '19.0 g'},
     '4222157.4': {'mouse #': '4222157.4', 'species': 'mus musculus', 'ID': 'FD1', 'DOB': '2019-02-08 00:00:00',
                   'genotype': 'CaMKII-cre hemizygous', 'sex': 'MALE', 'virus injection date': '2019-05-02 00:00:00',
                   'VIRUS': 'AAV1-CAG-FLEX-GCaMP6f-WPRE', 'cannula implant date': '2019-05-02 00:00:00',
                   'weight at time of implant': '26.2 g'},
     '4222169.1': {'mouse #': '4222169.1', 'species': 'mus musculus', 'ID': 'FD2', 'DOB': '2019-03-03 00:00:00',
                   'genotype': 'CaMKII-cre hemizygous', 'sex': 'FEMALE', 'virus injection date': '2019-07-10 00:00:00',
                   'VIRUS': 'AAV1-CAG-FLEX-GCaMP6f-WPRE', 'cannula implant date': '2019-07-10 00:00:00',
                   'weight at time of implant': '22.3 g'},
     '4222169.2': {'mouse #': '4222169.2', 'species': 'mus musculus', 'ID': 'FD3', 'DOB': '2019-03-03 00:00:00',
                   'genotype': 'CaMKII-cre hemizygous', 'sex': 'FEMALE', 'virus injection date': '2019-07-10 00:00:00',
                   'VIRUS': 'AAV1-CAG-FLEX-GCaMP6f-WPRE', 'cannula implant date': '2019-07-10 00:00:00',
                   'weight at time of implant': '18.7 g'},
     '4222169.4': {'mouse #': '4222169.4', 'species': 'mus musculus', 'ID': 'FD4', 'DOB': '2019-03-31 00:00:00',
                   'genotype': 'CaMKII-cre hemizygous', 'sex': 'FEMALE', 'virus injection date': '2019-07-12 00:00:00',
                   'VIRUS': 'AAV1-CAG-FLEX-GCaMP6f-WPRE', 'cannula implant date': '2019-07-12 00:00:00',
                   'weight at time of implant': '21.7 g'}}
