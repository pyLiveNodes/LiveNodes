import glob 
import h5py

fs = glob.glob("./**/*.h5")
for f in fs:
    print(f)
    with h5py.File(f, "r+") as dataFile:
        data = dataFile.get("data")[:] -1
        del dataFile["data"]
        dataFile.create_dataset("data", shape=data.shape, data=data, dtype="float16")