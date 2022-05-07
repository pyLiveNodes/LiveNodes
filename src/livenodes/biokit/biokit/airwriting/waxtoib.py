import numpy
import argparse
import adc


class WaxToIb():
    """
    Convert data recorded with WAX9 at the wrist to InertialBlue data
    recorded at the back of the hand.
    """

    def __init__(self):
        default_base = "/project/AMR/Handwriting/wrist/transform/scripts/"
        self.config = {
            "transformation_b_file":
            "%stransform_b_nonorm_multiple" % default_base,
            "transformation_T_file":
            "%stransform_T_nonorm_multiple" % default_base,
            "transformation_c_file":
            "%stransform_c_nonorm_multiple" % default_base,
            "wax9_sampling_rate": 200,
            "inertial_blue_sampling_rate": 819.2
        }

    def convert(self, data):
        """
        Converts data to the new coordinate system
        
        Data must be given as numpy array with time as first index and
        channels as second and channel order 
        (counter, acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z)
        
        Keyword arguments:
        data - numpy array (1st index is time, 2nd index is channels)
        """

        #treat counter seperately
        counter = data[:, 0]
        data_arr = data[:, 1:7]
        #first generally convert the different sensor coordinate systems
        data_arr = data_arr.dot(numpy.diag([-1, 1, 1, 1, -1, -1]))

        #scale the acc
        data_arr[:, 0:3] = 0.25 * data_arr[:, 0:3]

        b = numpy.loadtxt(self.config["transformation_b_file"])
        T = numpy.loadtxt(self.config["transformation_T_file"])
        c = numpy.loadtxt(self.config["transformation_c_file"])

        #actual transform
        data_arr = b * data_arr.dot(T) + c

        points = (len(data_arr) * 1.0) / \
            self.config["wax9_sampling_rate"] * \
            self.config["inertial_blue_sampling_rate"]
        #data_arr = scipy.signal.resample(data_arr, points)
        data_arr = self._resample(data_arr, int(points))
        counter = self._resample(counter, int(points))

        #enforce shorts!
        data_arr = numpy.clip(data_arr, -32767, 32766)
        counter = numpy.clip(counter, -32767, 32766)

        #channel permutation (swap acc and gyro)
        data_acc = data_arr[:, 0:3]
        data_gyro = data_arr[:, 3:6]
        retdata = numpy.concatenate((counter, data_gyro, data_acc), 1)

        return retdata

    def _resample(self, input_array, target_nr):
        in_t = numpy.atleast_2d(input_array.T)
        out_t = []
        source_nr = len(in_t[0])
        for ch in in_t:
            if len(ch) > 0:
                trgt = numpy.linspace(0, source_nr - 1, target_nr)
                trgt_vls = numpy.interp(trgt, list(range(source_nr)), ch)
                out_t.append(trgt_vls)
            else:
                out_t.append(numpy.array([]))
        return numpy.array(out_t).T

    def convertfile(self, infile, outfile):
        indata = adc.read(infile, 14)
        seldata = indata[:, 2:9]
        outdata = self.convert(seldata)
        adc.write(outdata, outfile)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert WAX9 to IB coordinates")
    parser.add_argument("infile", help="input wax (14channel) adc file")
    parser.add_argument("outfile", help="output ib (7channel) adc file")
    parser.add_argument("-p",
                        "--plot",
                        action="store_true",
                        help="plot in- and output")
    args = parser.parse_args()

    wax2ib = WaxToIb()

    indata = adc.read(args.infile, 14)
    inseldata = indata[:, 2:9]
    outseldata = wax2ib.convert(inseldata)
    adc.write(outseldata, args.outfile)
    if args.plot:
        import matplotlib.pyplot as plt
        plt.figure(1)
        plt.title("wax data")
        plt.plot(inseldata)
        plt.figure(2)
        plt.title("converted data")
        plt.plot(outseldata)
        plt.show()
