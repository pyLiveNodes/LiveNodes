import argparse
import adc
from .wkmb2 import WKM
from .mathlib import whiten
from matplotlib import pyplot as plt
import matplotlib.colors as colors
import matplotlib.cm as cmx


def plot_clustered(data, boundaries):
    f = plt.figure()
    plt.plot(data)
    for b in boundaries:
        plt.axvline(x=b)
    plt.show()


def plot_clusters(wkmobj):
    jet = plt.get_cmap('jet')
    cNorm = colors.Normalize(vmin=0, vmax=wkmobj.numclusters)
    scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=jet)
    nrsamples = len(wkmobj.samplelist)
    f = plt.figure()
    for i in range(nrsamples):
        plt.subplot(nrsamples, 1, i)
        #plt.plot( wkmobj.samplelist[i])
        for clusteridx, b in enumerate(wkmobj.boundaries[i]):
            samples = wkmobj.samplelist[i]
            xvalues = list(range(len(samples)))
            color = scalarMap.to_rgba(clusteridx)
            start = b
            if clusteridx < wkmobj.numclusters - 1:
                end = wkmobj.boundaries[i][clusteridx + 1]
            else:
                end = len(wkmobj.boundaries[i]) - 1
            plt.plot(xvalues[start:end], samples[start:end], color=color)
            plt.axvline(x=b)
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="perform warped " +
                                     "k-means clustering")
    parser.add_argument("adcfiles", nargs="+", help="input adc files")
    parser.add_argument("dim", type=int, help="dimensions in file")
    parser.add_argument("k", help="number of clusters")
    parser.add_argument("-delta",
                        type=float,
                        help="delta parameter",
                        default=0.0)
    parser.add_argument("-strip",
                        type=bool,
                        help="delete last channel (counter)")

    args = parser.parse_args()

# Read data samples
data = []
for filename in args.adcfiles:
    with open(filename) as fh:
        data.append(adc.read(fh, args.dim))

if args.strip:
    for i, d in enumerate(data):
        data[i] = data[i][:, 1:7]
for i, d in enumerate(data):
    data[i] = data[i].tolist()
    data[i] = whiten(data[i])

w = WKM(data, args.k, args.delta)
w.cluster_init()
cont = True
while cont:
    cont = w.cluster_iter()
    #plot_clusters(w)
w.cluster_finalize()

print("boundaries:", w.boundaries)
#print "clusters:",      w.clusters
print("centroids:", w.centroids)
print("localenergy:", w.localenergy)
print("totalenergy:", w.totalenergy)
print("iterations:", w.iterations)
print("numtransfers:", w.numtransfers)
print("cost:", w.cost)

# do some nice plotting
vis = True
if vis:
    plot_clusters(w)
