import unittest
import os
from pathlib import Path
from tempfile import mkdtemp
from shutil import rmtree
from jsonschema import validate, RefResolver

import pytest

from nwb_conversion_tools.utils.json_schema import load_dict_from_file

# Path to dataset downloaded from https://gin.g-node.org/NeuralEnsemble/ephy_testing_data
#   ecephys: https://gin.g-node.org/NeuralEnsemble/ephy_testing_data
#   ophys: TODO
#   icephys: TODO
if os.getenv("CI"):
    LOCAL_PATH = Path(".")  # Must be set to "." for CI
    print("Running GIN tests on Github CI!")
else:
    LOCAL_PATH = Path("/home/jovyan/")  # Override this on personal device for local testing
    print("Running GIN tests locally!")

DATA_PATH = LOCAL_PATH / "ephy_testing_data"
HAVE_DATA = DATA_PATH.exists()

if not HAVE_DATA:
    pytest.fail(f"No ephy_testing_data folder found in location: {DATA_PATH}!")


class TestYAML(unittest.TestCase):
    def setUp(self):
        self.test_folder = Path(mkdtemp())

    def tearDown(self):
        rmtree(path=self.test_folder)

    def test_validate_example_specification(self):
        path_to_test_gin_file = Path(__file__)
        yaml_file_path = path_to_test_gin_file.parent / "GIN_converter_specification.yml"
        specification = load_dict_from_file(file_path=yaml_file_path)
        schema_folder = Path(__file__).parent.parent.parent / "nwb_conversion_tools" / "schemas"
        specification_schema = load_dict_from_file(file_path=schema_folder / "yaml_specification_schema.json")
        validate(
            instance=specification,
            schema=specification_schema,
            resolver=RefResolver(base_uri="file://" + str(schema_folder) + "/", referrer=specification_schema),
        )


if __name__ == "__main__":
    unittest.main()
