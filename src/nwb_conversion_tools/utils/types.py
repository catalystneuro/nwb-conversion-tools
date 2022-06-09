"""Authors: Luiz Tauffer, Cody Baker, Saksham Sharda and Ben Dichter."""
from pathlib import Path
from typing import Optional, Union
from typing import TypeVar

import numpy as np
from numpy.typing import ArrayLike, DTypeLike

FilePathType = TypeVar("FilePathType", str, Path)
FolderPathType = TypeVar("FolderPathType", str, Path)
OptionalFilePathType = Optional[FilePathType]
OptionalFolderPathType = Optional[FolderPathType]
ArrayType = ArrayLike
DtypeType = DTypeLike
OptionalArrayType = Optional[ArrayType]
FloatType = float
IntType = Union[int, np.integer]
