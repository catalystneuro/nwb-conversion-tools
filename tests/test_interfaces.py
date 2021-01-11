from jsonschema import Draft7Validator

import spikeextractors as se
from spikeextractors.tests.utils import check_sortings_equal

from nwb_conversion_tools import NWBConverter, interface_list


def test_interface_schemas():
    for data_interface in interface_list:
        # check validity of source schema
        schema = data_interface.get_source_schema()
        Draft7Validator.check_schema(schema)

        # check validity of conversion options schema
        schema = data_interface.get_conversion_options_schema()
        Draft7Validator.check_schema(schema)


def test_add_sorting_extractor():
    sorting_extractor = se.example_datasets.toy_example()[1]
    converter = NWBConverter(source_data=dict())
    converter.add_sorting_extractor(sorting_extractor=sorting_extractor)

    interface_name = 'NumpySorting'
    interface_class_name = 'NumpySortingExtractorDataInterface'
    extractor_name = 'NumpySortingExtractor'
    assert interface_name in converter.data_interface_classes
    assert interface_name in converter.data_interface_objects
    assert interface_class_name == converter.data_interface_classes[interface_name]
    assert interface_class_name == converter.data_interface_objects[interface_name].__name__
    assert extractor_name == converter.data_interface_objects[interface_name].SX
    check_sortings_equal(sorting_extractor, converter.data_interface_objects[interface_name].sorting_extractor)
