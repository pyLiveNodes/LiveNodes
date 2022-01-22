import math
from .mathlib import cumdist, sqL2, clustercenter

class WKM:
  """
  Warped K-Means: an algorithm to cluster sequentially-distributed data.
  Luis A. Leiva and Enrique Vidal. Information Sciences, 2013.
  See http://dx.doi.org/10.1016/j.ins.2013.02.042
  Implemented by Luis A. Leiva.
  Dual licensed under the MIT and GPL licenses.
  Project page: http://personales.upv.es/luileito/wkm/

  Extension to find clusters over multiple datasamples.
  """
  
  def __init__(self, samplelist, numclusters, threshold=0.0, minsize=50):
    """
    Instantiate the class.
    Threshold is the cluster population that will be tested in each iteration.
    
    samplelist - list of samples
    """
    self.maxiter = 100
    # User input
    self.samplelist  = samplelist
    self.numclusters = int(numclusters)
    self.threshold   = float(threshold)
    self.minsize     = int(minsize)
    # Assume that all samples have the same dimensions
    self.dimensions = len(self.samplelist[0][0])
    self.minsamplelen = min([len(s) for s in samplelist])
    # Sanitize user input
    if self.numclusters < 1:
      self.numclusters = 1
    elif self.numclusters > self.minsamplelen:
      self.numclusters = self.minsamplelen
    if threshold > 1:
      self.threshold = 1.0
    elif threshold < 0:
      self.threshold = 0.0
    self.reset()


  def reset(self):
    """Clean up."""
    self.initialized  = False
    # System ouput
    self.boundaries   = [0] * self.numclusters
    self.clusters     = [0] * self.numclusters
    self.centroids    = [0] * self.numclusters
    self.localenergy  = [0] * self.numclusters
    self.totalenergy  = 0.0
    self.iterations   = 0
    self.numtransfers = 0
    self.cost         = 0


  def init(self, method=None):
    """Initialization method."""
    self.reset()
    N, M = self.minsamplelen, self.numclusters
    # Silly checks
    if self.numclusters <= 1: # single partition
      self.boundaries = [0]
      return  
    elif self.numclusters >= N: # singleton clusters
      self.boundaries = [i for i in range(N)]
      return
    # Finally check user-defined method
    if method == None:
      self.initdefault(N,M)
    else:
      method = method.lower()
      if method == "ts":
        self.TS(N,M)
      elif method == "eq":
        self.resample(N,M)
      else: 
        self.initdefault(N,M)


  def initdefault(self, N, M):
    """
    Default boundaries initialization. 
    Will use TS only if 2M <= N (~ Nyquist).
    Other methods may be implemented, as long as they process samples in a sequential fashion.
    """
    self.boundaries = []
    if N/float(M) < 2:
      self.resample(N,M)
    else:
      self.TS(N,M)
    self.resample(N,M)
    
    
  def TS(self, N, M):
    """
    Initialize boundaries by trace segmentation (non-linear allocation). 
    This is the pre-set initialization mode.
    """
    self.boundaries = []
    for samples in self.samplelist:
      boundaries = []
      Lcum, LN = cumdist(samples)
      incr, i = LN / float(M), 0
      for j in range(1,M+1):
        fact = (j - 1)*incr
        while fact > Lcum[i] or i in boundaries:
          i += 1
        boundaries.append(i) 
      self.boundaries.append(boundaries)
    self.initialized = True
    
    
  def resample(self, N, M):
    """Allocate N points into M boundaries in a linear fashion (see t8 APP)."""
    self.boundaries = []
    for samples in self.samplelist:
      boundaries = []
      b = -1
      for i in range(N):
        q = math.floor( (i+1)*M/(N+1.0) )
        if q > b:
          b = q
          boundaries.append(i)
      self.boundaries.append(boundaries)
    self.initialized = True
    

  def getPartition(self):
    """
    Fill the cluster data structure with the points.
    """
    for j in range(self.numclusters):
      self.clusters[j] = self.getClusterSamples(j)
      #assert len(self.clusters[j]) > 0, "Empty cluster %d" % j


  def getClusterSamples(self, index):
    """
    Retrieve points by cluster index.
    
    Points of all sample clusters are merged.

    Keyword arguments:
    index - index of the global cluster
    """
    points = []
    for sampleidx, samples in enumerate(self.samplelist):
      start = self.boundaries[sampleidx][index]
      if index+1 < self.numclusters:
        end = self.boundaries[sampleidx][index+1]
      else:
        end = len(samples)
      points.extend(samples[start:end])
    return points

  def getClusterSamplesLocal(self, clusteridx, sampleidx):
    """
    Retrieve points of cluster for a specific sample.

    Keyword arguments:
    clusteridx - index of the cluster
    sampleidx - index of the sample
    """
    samples = self.samplelist[sampleidx]
    start = self.boundaries[sampleidx][clusteridx]
    if clusteridx+1 < self.numclusters:
      end = self.boundaries[sampleidx][clusteridx+1]
    else:
      end = len(samples)
    points = samples[start:end]
    return points


  def setPartition(self, partitionlist):
    """
    Specify a sequential cluster configuration.
    """
    self.boundaries, self.clusters = [], []
    for partition in partitionlist:
      boundaries = [0]
      for j, points in enumerate(partition):
        #assert len(points) > 0, "Empty cluster %d" % j
        self.clusters[j].extend(points)
        if j > 0:
          self.boundaries.append(len(points)-1)
      self.boundaries.append(boundaries)
      


  def computeEnergies(self):
    """
    Compute the energy of all clusters from scratch.
    """
    self.totalenergy = 0.0
    for j in range(self.numclusters):
      points = self.clusters[j]
      #assert len(points) > 0, "Empty cluster %d" % j
      self.centroids[j] = clustercenter(points)
      energy = 0.0
      for pt in points:
        energy += sqL2(pt, self.centroids[j])
      self.localenergy[j] = energy
      self.totalenergy += energy


  def incrementalMeans(self, sample, j, b, n, m):
    """
    Recompute cluster means as a result of reallocating a sample to a better cluster.
    
    sample - one sample given as list (len = dimensionality)
    j - cluster from which sample is taken
    b - cluster to which sample is assigned
    n - 
    m - 
    """
    newj = [0.0] * self.dimensions
    newb = newj[:]
    for d in range(self.dimensions):
      newb[d] = self.centroids[b][d] + (sample[d] - self.centroids[b][d]) / (m + 1.0)
      newj[d] = self.centroids[j][d] - (sample[d] - self.centroids[j][d]) / (n - 1.0)
    self.centroids[b] = newb
    self.centroids[j] = newj
    

  def cluster_init(self, partition=None):
    """Perform sequential clustering."""
    if not self.initialized:
      self.init()
    if partition:
      self.setPartition(partition)
    else:
      self.getPartition()
    self.computeEnergies()
    # Silly check
    if self.numclusters < 2:
      return
  def cluster_iter(self):
    # Reallocate boundaries
      transfers = False # no transfers yet
      print(("******** Iteration %s *********" % self.iterations))
      for j in range(self.numclusters):
        #print("cluster index: %s" % j)
        for sampleidx, samples in enumerate(self.samplelist):
          #print("sample index: %s" % sampleidx)
          if j > 0:
            ### c = self.clusters[j][:]
            c = self.getClusterSamplesLocal(j, sampleidx)
            n = len(c)
            #print("local cluster: size: %s" % n)
            # Reallocate backward 1st half
            for i in range(0, int(math.floor(n/2.0 * (1 - self.threshold))) + 1):
              p = c[i]
              b = j - 1
              m = len(self.clusters[b])
              n = len(self.clusters[j])
              if len(self.getClusterSamplesLocal(j, sampleidx)) < self.minsize: break
              J1 = (m / (m + 1.0)) * sqL2(p, self.centroids[b])
              J2 = (n / (n - 1.0)) * sqL2(p, self.centroids[j])
              delta = J1 - J2
              self.cost += 1
              if delta < 0:
                transfers = True
                self.numtransfers += 1
                self.boundaries[sampleidx][j] += 1
                self.incrementalMeans(p,j,b,n,m)
                self.localenergy[b] += J1
                self.localenergy[j] -= J2
                self.totalenergy += delta
                self.getPartition()
              else: break
            #print("backward relocation: %s" % i)
          if j + 1 < self.numclusters:
            c = self.getClusterSamplesLocal(j, sampleidx)
            n = len(c)
            #print("local cluster size: %s" % n)
            ## Reallocate forward 2nd half
            for i in range(n-1, int(math.floor(n/2.0 * (1 + self.threshold))) - 2, -1):
              p = c[i]
              b = j + 1
              m = len(self.clusters[b])
              n = len(self.clusters[j])
              if len(self.getClusterSamplesLocal(j, sampleidx)) < self.minsize: break
              J1 = (m / (m + 1.0)) * sqL2(p, self.centroids[b])
              J2 = (n / (n - 1.0)) * sqL2(p, self.centroids[j])
              delta = J1 - J2
              self.cost += 1
              if delta < 0:
                transfers = True
                self.numtransfers += 1
                self.boundaries[sampleidx][b] -= 1
                self.incrementalMeans(p,j,b,n,m)
                self.localenergy[b] += J1
                self.localenergy[j] -= J2
                self.totalenergy += delta
                self.getPartition()
              else: break
            #print("forward relocation: %s" % i)
      self.iterations += 1
      if not transfers or self.iterations == self.maxiter:
          return False
      else:
          return True

  def cluster_finalize(self):
    # Finally, recompute energies from scratch when algorithm converges, to avoid rounding errors
    self.computeEnergies()

