from jsonschema import Draft7Validator
import numpy as np

import cv2

from nwb_conversion_tools import interface_list
from nwb_conversion_tools import NWBConverter
from nwb_conversion_tools.datainterfaces.moviedatainterface import MovieInterface


def test_interface_schemas():
    for data_interface in interface_list:
        # check validity of source schema
        schema = data_interface.get_source_schema()
        Draft7Validator.check_schema(schema)

        # check validity of conversion options schema
        schema = data_interface.get_conversion_options_schema()
        Draft7Validator.check_schema(schema)


def test_movie_interface():
    movie_file = "test1.avi"
    nwbfile_path = "test1.nwb"
    (nf, nx, ny) = (50, 640, 480)
    writer = cv2.VideoWriter(movie_file, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'), 25, (ny, nx), True)
    for k in range(nf):
        writer.write(np.random.randint(0, 255, (nx, ny, 3)).astype('uint8'))
    writer.release()

    class MovieTestNWBConverter(NWBConverter):
        data_interface_classes = dict(Movie=MovieInterface)
    source_data = dict(Movie=dict(file_paths=[movie_file]))
    converter = MovieTestNWBConverter(source_data)
    metadata = converter.get_metadata()
    converter.run_conversion(metadata=metadata, nwbfile_path=nwbfile_path, overwrite=True)
