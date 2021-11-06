import json
from pathlib import Path
from typing import Union
import os

from nwb_conversion_tools.utils.json_schema import get_schema_from_method_signature, dict_deep_update, fill_defaults
from nwb_conversion_tools.utils.metadata import load_metadata_from_file


def compare_dicts(a: dict, b: dict):
    a = sort_dict(a)
    b = sort_dict(b)
    assert json.dumps(a, indent=2) == json.dumps(b, indent=2)


def compare_dicts_2(a: dict, b: dict):
    a = sort_dict(a)
    b = sort_dict(b)
    assert json.dumps(a) == json.dumps(b)


def sort_dict(a: dict):
    b = {i:a[i] for i in sorted(a)}
    for key, val in b.items():
        if isinstance(val, dict):
            b[key] = sort_dict(val)
        elif isinstance(val, list):
            b[key] = sort_list(val)
    return b


def sort_list(b: list):
    b.sort(key=str)
    for bb in b:
        if isinstance(bb, list):
            b = sort_list(b)
        elif isinstance(bb, dict):
            b = sort_dict(bb)
    return b


def test_get_schema_from_method_signature():
    class A:
        def __init__(self, a: int, b: float, c: Union[Path, str], d: bool, e: str = "hi"):
            pass

    schema = get_schema_from_method_signature(A.__init__)

    correct_schema = dict(
        additionalProperties=False,
        properties=dict(
            a=dict(type="number"),
            b=dict(type="number"),
            c=dict(type="string"),
            d=dict(type="boolean"),
            e=dict(default="hi", type="string"),
        ),
        required=[
            "a",
            "b",
            "c",
            "d",
        ],
        type="object",
    )

    compare_dicts(schema, correct_schema)


def test_dict_deep_update():
    # 1. dict with non dict, list items
    a1 = dict(a=1, b="hello", c=23)
    b1 = dict(a=3, b="goodbye", d="compare")
    result1 = dict_deep_update(a1, b1, copy=True)
    correct_result = dict(a=3, b="goodbye", c=23, d="compare")
    compare_dicts(result1, correct_result)

    # 2. test recursive dicts as keys
    a2 = dict(a=1, c=a1)
    b2 = dict(a=3, b="compare", c=b1)
    result2 = dict_deep_update(a2, b2, copy=True)
    correct_result = dict(a=3, b="compare", c=result1)
    compare_dicts(result2, correct_result)

    # 3.1 test list single elements append
    a3 = dict(a2, ls1=[1, 2, "test"])
    b3 = dict(b2, ls1=[3, 1, "test2"])
    result3_1 = dict_deep_update(a3, b3, copy=True, append_list=True)
    correct_result = dict(result2, ls1=[1, 2, 3, "test", "test2"])
    compare_dicts(result3_1, correct_result)
    result3_1 = dict_deep_update(a3, b3, copy=True, append_list=True, remove_repeats=False)
    correct_result = dict(result2, ls1=[1, 1, 2, 3, "test", "test2"])
    compare_dicts(result3_1, correct_result)
    # 3.2 test without append
    result3_2 = dict_deep_update(a3, b3, copy=True, append_list=False)
    correct_result = dict(result2, ls1=b3["ls1"])
    compare_dicts(result3_2, correct_result)

    # 4. test list of dicts with common keys
    c1 = dict(a1, b="world", e="string")
    a4 = dict(a3, ls1=[a1, b1])
    b4 = dict(b3, ls1=[c1])
    # compare key is common in both:
    result4 = dict_deep_update(a4, b4, copy=True, compare_key="a")
    correct_result = dict(result3_1, ls1=[dict_deep_update(a1, c1, copy=True), b1])
    compare_dicts(result4, correct_result)
    # compare key missing:
    result4 = dict_deep_update(a4, b4, copy=True, compare_key="b")
    correct_result = dict(result3_1, ls1=[a1, c1, b1])
    compare_dicts(result4, correct_result)


def test_fill_defaults():

    schema = dict(
        additionalProperties=False,
        properties=dict(
            a=dict(type="number"),
            b=dict(type="number"),
            c=dict(type="string"),
            d=dict(type="boolean"),
            e=dict(default="hi", type="string"),
        ),
        required=[
            "a",
            "b",
            "c",
            "d",
        ],
        type="object",
    )

    defaults = dict(a=3, c="bye", e="new")

    fill_defaults(schema, defaults)

    correct_new_schema = dict(
        additionalProperties=False,
        properties=dict(
            a=dict(type="number", default=3),
            b=dict(type="number"),
            c=dict(type="string", default="bye"),
            d=dict(type="boolean"),
            e=dict(default="new", type="string"),
        ),
        required=[
            "a",
            "b",
            "c",
            "d",
        ],
        type="object",
    )

    compare_dicts(schema, correct_new_schema)


def test_load_metadata_from_file():
    m0 = dict(
        NWBFile=dict(
            experimenter="Mr Tester",
            identifier="abc123",
            institution="My University",
            lab="My lab",
            session_description="testing conversion tools software",
            session_start_time="2020-04-15T10:00:00+00:00",
        ),
        Subject=dict(
            description="ADDME",
            sex="M",
            species="ADDME",
            subject_id="sid000",
            weight="10g",
            date_of_birth="2020-04-07T00:15:00+00:00",
        ),
        Ecephys=dict(
            Device=[dict(name="device_ecephys")],
            ElectricalSeries=[
                dict(description="ADDME", name="ElectricalSeries", rate=10.0, starting_time=0.0, conversion=1.0)
            ],
            ElectrodeGroup=[
                dict(description="ADDME", device="device_ecephys", location="ADDME", name="ElectrodeGroup")
            ],
        ),
    )

    yaml_file = os.path.join(os.path.dirname(__file__), "metadata_tests.yml")
    json_file = os.path.join(os.path.dirname(__file__), "metadata_tests.json")

    m1 = load_metadata_from_file(file=yaml_file)
    compare_dicts_2(m0, m1)

    m2 = load_metadata_from_file(file=json_file)
    compare_dicts_2(m0, m2)
