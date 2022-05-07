import numpy as np
import struct

#define float matrix (.fmat) header
fmat_header_dtype = np.dtype([
    ("format_id", "S4"),  #needs to be FMAT
    ("rows", ">i4"),
    ("columns", ">i4"),
    ("unused", ">f4")
])


def loadFloatMatrix(filename):
    """
    Load a matrix in float matrix (.fmat) format into a numpy array.

    Keyword arguments:
    filename -- filename of the .fmat file
    """
    with open(filename) as fh:
        header = np.fromfile(fh, dtype=fmat_header_dtype, count=1)
        data = np.fromfile(fh, dtype=">f4")
    data = np.reshape(data, (header['rows'][0], header['columns'][0]))
    return data


def writeFloatMatrix(array, filename):
    """
    Save a numpy array in float matrix (.fmat) format.

    Keyword arguments:
    array -- the numpy array, must be a two dimensional float array
    """
    rows, cols = array.shape
    header = struct.pack(">4siif", "FMAT", rows, cols, 0.0)
    nrelements = rows * cols
    data = struct.pack(">" + nrelements * "f", *(array.flatten()))
    with open(filename, "w") as fh:
        fh.write(header)
        fh.write(data)
