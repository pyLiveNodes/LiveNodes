import argparse
import adc
from .wkmb import WKM
from .mathlib import whiten
from matplotlib import pyplot as plt


def plot_clustered(data, boundaries):
    f = plt.figure()
    plt.plot(data)
    for b in boundaries:
        plt.axvline(x=b)
    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="perform warped " +
                "k-means clustering")
    parser.add_argument("adc", help="input adc file")
    parser.add_argument("dim", type=int, help="dimensions in file")
    parser.add_argument("k", help="number of clusters")
    parser.add_argument("-delta", type=float, 
                        help="delta parameter", default=0.0)
    parser.add_argument("-strip", type=bool, 
                        help="delete last channel (counter)")
    
    args = parser.parse_args()

# Read data samples
with open(args.adc) as fh:
    data = adc.read(fh, args.dim)
if args.strip:
    data = data[:,1:]
datalist = data.tolist()
# Do some cleanup and convert data to list

w = WKM(whiten(datalist), args.k, args.delta)
w.cluster()

print("boundaries:",    w.boundaries)
#print "clusters:",      w.clusters
print("centroids:",     w.centroids)
print("localenergy:",   w.localenergy)
print("totalenergy:",   w.totalenergy)
print("iterations:",    w.iterations)
print("numtransfers:",  w.numtransfers)
print("cost:",          w.cost)

# do some nice plotting
plot_clustered(data, w.boundaries)
