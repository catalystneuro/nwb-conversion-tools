from ..base_interface_icephys_neo import BaseIcephysNeoInterface
from neo import AxonIO


class AbfNeoDataInterface(BaseIcephysNeoInterface):
    """ABF DataInterface based on Neo AxonIO"""

    neo_class = AxonIO