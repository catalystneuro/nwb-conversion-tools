from nwb_conversion_tools import AbfNeoDataInterface, NWBConverter
from pathlib import Path
import pandas as pd

   

# electrode_metadata = dict(
#     name='name', 
#     device, 
#     description, 
#     slice=None, seal=None, location=None, resistance=None, filtering=None, initial_access_resistance=None
# )    

# for f in file_list:
#     file_recordings_metadata = dict(
#         stimulus_type='type',
#         table_indexes=dict(
#             SimultaneousRecordings_index=0,
#             SequentialRecordings_index=0,
#             Repetitions_index=0
#             ExperimentalConditions_index=0
#         )
#     )



def run_conversion(source_dir, output_file=None, metadata_file=None, icephys_experiment_type=None):
    directory = Path(source_dir)
    files_list = list()
    for x in directory.iterdir():
        if x.is_file() and x.suffix == '.abf':
            files_list.append(str(x.resolve()))

    # Makes a Converter with different number of DataInterfaces, depending on
    # how many files the same session is broken into.
    class GuagweiConverter(NWBConverter):
        data_interface_classes = {
            f"AbfNeoDataInterface_{i}": AbfNeoDataInterface
            for i, _ in enumerate(files_list)
        }

    # Instantiate Converter
    source_data = {
        f"AbfNeoDataInterface_{i}": dict(file_path=f)
        for i, f in enumerate(files_list)
    }
    converter = GuagweiConverter(source_data=source_data)

    # Set metadata details
    metadata = converter.get_metadata()
    if metadata_file is not None and Path(metadata_file).suffix == '.csv':
        metadata_df = pd.read_csv(metadata_file)
        subject_id = Path(source_dir).name
        metadata_df = metadata_df[metadata_df.subject_id == int(subject_id)]
        stimulus_type_list = metadata_df['session_description'].tolist()

        metadata['IntracellularRecordings'] = [
            {
                "sequence_id": i,
                "stimulus_type": stimulus_type_list[i],
            } for i, f in enumerate(files_list)
        ]

    # Set conversion options
    if icephys_experiment_type is None:
        icephys_experiment_type='current_clamp'
    conversion_options = {
        f"AbfNeoDataInterface_{i}": dict(icephys_experiment_type=icephys_experiment_type)
        for i, _ in enumerate(files_list)
    }

    if output_file is None:
        output_file = 'out_example.nwb'

    converter.run_conversion(
        metadata=metadata, 
        nwbfile_path=output_file, 
        save_to_file=True,
        overwrite=True,
        conversion_options=conversion_options
    )
