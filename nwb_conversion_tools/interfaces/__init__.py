import typing


from nwb_conversion_tools.interfaces.base_data import BaseDataInterface
from nwb_conversion_tools.interfaces import imaging, interface_utils, recording, segmentation, sorting
from nwb_conversion_tools.utils import _recursive_import, _recurse_subclasses


def list_interfaces(interface_type: typing.Optional[str] = None) -> typing.List[typing.Type[BaseDataInterface]]:
    """
    List all available data interfaces as a flat list, disregarding extractor subtype

    Imports modules within :mod:`nwb_conversion_tools.interfaces` (or sub-module, if interface_type is provided)
    and lists __subclasses__ of :class:`.interfaces.BaseDataInterface` recursively.

    Args:
        interface_type (None, str): if None, list all interfaces. Otherwise, if some interface
            subtype if provided (eg. ``'imaging'``, ``'recording'``), only list interfaces of that type.

    Returns:
        list: list of data interfaces inheriting from :class:`.interfaces.BaseDataInterface`

    Examples:

        List all interfaces::

            all_interfaces = list_interfaces()

        List all recording interfaces::

            recording_interfaces = list_interfaces('recording')
    """

    # recursively import all submodules in interfaces so they're in sys.modules
    import_module = "nwb_conversion_tools.interfaces"
    if interface_type is not None:
        import_module = '.'.join([import_module, interface_type])

    _recursive_import(import_module)
    return _recurse_subclasses(BaseDataInterface)

