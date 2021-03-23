from jsonschema import Draft7Validator

from nwb_conversion_tools import interfaces


def test_interface_schemas():
    for data_interface in interfaces.list_interfaces():
        
        # check validity of source schema
        schema = data_interface.get_source_schema()
        Draft7Validator.check_schema(schema)

        # check validity of conversion options schema
        schema = data_interface.get_conversion_options_schema()
        Draft7Validator.check_schema(schema)
