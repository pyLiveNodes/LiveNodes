import matplotlib.pyplot as plt
import matplotlib as mpl
import mpl_toolkits.axes_grid1 as axgrid
import numpy
import pdb

from matplotlib.mlab import normpdf

#global variable that defines if plots should go to files or to the screen
PLOTTARGET = None

"""
TODO:
- currently most of the code only works with GMMs, if it is changed to sample the
distribution values directly from the scorer it would be independent of the actual
underlying concrete scorer (individual gaussians could not be displayed in that case)
"""


class PathPlot(object):
    """
    Creates and manages a path plot with the according feature sequence.

    The individual Gaussian Mixtures can be visualized by clicking individual
    states in path plot.
    """

    def __init__(self, path, fs, sg, scorer, borders):
        """
        Create a path plot object (nothing is plotted yet)

        Keyword arguments:
        path - Instance of Path
        fs - Instance of FeatureSequence that generated the path
        sg - Instance of SearchGraph
        scorer - Instance of GmmFeatureVectorScorer
        borders - Additional borders that should be printed in the path
            (e.g. word or motion borders)
        """

        self.path = path
        self.fs = fs
        self.sg = sg
        self.scorer = scorer
        self.gaussMixtureSet = self.scorer.getGaussMixturesSet()
        self.borders = borders

    def on_pick(self, event):
        """
        Event hanlder for the on_pick event.

        Opens a new window with the GMM of the state that was clicked

        Keyword arguments:
        event - the pick event
        """
        thisline = event.artist
        xdata, ydata = thisline.get_data()
        ind = event.ind
        med = len(xdata[ind]) / 2
        print(('on pick line:', list(zip(xdata[ind], ydata[ind]))))
        modelName = self.modelNames[ydata[ind][med]]
        modelId = self.gaussMixtureSet.getModelId(modelName.encode('utf-8'))
        print(("selected model %s with id %s" % (modelName, modelId)))
        mixture = self.gaussMixtureSet.getGaussMixture(modelId)
        plot_mixture(mixture, style="line")
        show()

    def plot(self, name=None, colormap="Greys"):
        """
        Plots a path together with the feature sequence and the model distributions
        as an intensity map under the feature plot.

        Keyword arguments:
        name - name of the figure to create
        colormap - a valid matplotlib colormap or string identifier
        """
        self.fig = plt.figure(name)
        self.fig.canvas.mpl_connect('pick_event', self.on_pick)

        if self.borders is not None:
            self.pathax = self.fig.add_subplot(3, 1, 1)
            [self.pathax, self.mappedNodeIds, self.modelNames, self.xAxes] = \
                plotVitPath(self.path, self.sg, self.scorer, self.pathax)
            self.fsax = self.fig.add_subplot(3, 1, 2, sharex=self.pathax)
            self.fsax = plotFS(self.fs, self.fsax, self.xAxes, [])
            self.fsax = self.fig.add_subplot(3, 1, 3, sharex=self.pathax)
            self.fsax = plotFS(self.fs, self.fsax, [], self.borders)
        else:
            self.pathax = self.fig.add_subplot(2, 1, 1)
            [self.pathax, self.mappedNodeIds, self.modelNames, self.xAxes] = \
                plotVitPath(self.path, self.sg, self.scorer, self.pathax)
            self.fsax = self.fig.add_subplot(2, 1, 2, sharex=self.pathax)
            self.fsax = plotFS(self.fs, self.fsax, self.xAxes, [], color="b")
            # get the limits
            support = [ax.get_ylim() for ax in self.fsax]
            data = _get_mixture_values_of_path(self.path, self.gaussMixtureSet,
                                               support, 50)
            for i, ax in enumerate(self.fsax):
                extent = [0, len(self.path), support[i][0], support[i][1]]
                ax.imshow(data[i], extent=extent ,alpha=0.9, aspect='auto',
                          cmap=colormap, interpolation='nearest')
        plt.tight_layout()


class RecoVis(object):
    """
    Visualization for the Recognizer.
    """

    def __init__(self, recognizer):
        """
        Construct the visualization class for a given recognizer
        """
        self.recognizer = recognizer

    def plotpath(self, fs, path):
        """
        Plot a path together with feature sequence and model distributions.

        Keyword arguments:
        fs - instance of FeatureSequence
        path - instance of Path produced by this feature sequence
        """
        plot_path_feat(path, self.recognizer.getSearchGraph(),
                       self.recognizer.getScorer(), fs)

    def plotmixture(self, mixturename):
        """
        Plot a Gaussian mixture model

        Keyword arguments:
        mixturename - name of the mixture
        """
        gaussMixtureSet = self.recognizer.getScorer().getGaussMixturesSet()
        modelId = gaussMixtureSet.getModelId(mixturename.encode('utf-8'))
        mixture = gaussMixtureSet.getGaussMixture(modelId)
        plot_mixture(mixture, mixturename)


def plot_mcfs(mcfs,borders=[], name=None):
    '''
    plot all channels of a MultiChannelFeatureSequence in current figure

    The matplotlib show() function is not called, i.e. no window is drawn
    until show() is called explicitely.

    parameters:
    mcfs - MultiChannelFeatureSequence to plot
    borders - borders between different acitivities in the sequence
    name - name of the plot, will appear in window title. If not given, the
        matplotlib default will be used
    '''
    fig = plt.figure(name)
    nrchannels = len(mcfs)
    for nr, fs in enumerate(mcfs, start=1):
        curax = fig.add_subplot(nrchannels, 1, nr)
        plotFS(fs, curax, [], borders)
    return


def plot_fs(fs,borders=[], name=None):
    '''
    plot all columns of a feature sequence as line plot

    The matplotlib show() function is not called, i.e. no window is drawn
    until show() is called explicitely.

    parameters:
    fs - FeatureSequence object to plot
    borders - borders between different acitivities in the sequence
    name - name of the plot, will appear in window title. If not given, the
        matplotlib default will be used
    '''
    fig = plt.figure(name)
    curax = fig.add_subplot(1, 1, 1)
    plotFS(fs, curax, [], borders)
    return


def plotFS(fs, ax, xAxes, borders, layout="bottom", pad=0.05, color="b"):
    '''plot a feature sequence with one plot per column'''

    divider = axgrid.make_axes_locatable(ax)
    matrix = fs.getMatrix()
    allaxes = []
    for (i, col) in enumerate(matrix.T):
        if i==0:
            curax = ax
        else:
            curax = divider.append_axes(layout, size="100%", pad=pad,
                                        sharex=ax)
        curax.plot(col, color)
        curax.yaxis.set_major_locator(mpl.ticker.MaxNLocator(2))
        for x in xAxes:
            plt.axvline(x=x, color='r')
        for x in borders:
            plt.axvline(x=x, color='g')
        allaxes.append(curax)
    return(allaxes)


def plotVitPath(path, sg, scorer, ax):
    '''plot a viterbi path'''
    xAxes = []
    mappedNodeIds = []
    modelNames = []
    ylabels = []
    lastStateId = None
    lastAtomId = None
    countX = -1
    countY = -1
    for pi in path:
        countX = countX + 1
        # need to check atom id too because state id starts with 0 for each HMM
        if (pi.mStateId != lastStateId) or (pi.mAtomId != lastAtomId):
            countY = countY + 1
            name = scorer.getModelName(pi.mModelId)
            #print(name)
            modelNames.append(name.decode('utf-8'))
            if (name[-2:] == '-0'):
                ylabels.append(name.decode('utf-8'))
                xAxes.append(countX)
            else:
                ylabels.append(' ')
        mappedNodeIds.append(countY)
        lastStateId = pi.mStateId
        lastAtomId = pi.mAtomId
    ax.plot(mappedNodeIds, 'bo-', picker=1)
    for x in xAxes:
        plt.axvline(x=x, color='r')
    #print(ylabels)
    #plt.yticks(range(len(ylabels)), ylabels)
    def statelabels(x, pos):
        #print(x)
        if x % 1 == 0 and int(x) in range(len(modelNames)):
            return modelNames[int(x)]
        else:
            return ""
    formatter = mpl.ticker.FuncFormatter(statelabels)
    ax.yaxis.set_major_formatter(formatter)
    return [ax, mappedNodeIds, modelNames, xAxes]


def plotHistoPerChannel(data, bins=20):
    """
    Plots a histogram for each column of the data matrix.

    Keyword arguments:
    data - a numpy array
    bins - number of bins to use (default 20)
    """
    plt.figure()
    n = data.shape[1]
    for i in range(n):
        plt.subplot(n, 1, i)
        plt.hist(data[:, i], bins=bins)


def plot_path_feat(path, sg, scorer, fs, borders=None, name=None):
    '''
    Plot a path object aligned with the feature sequence

    Keyword arguments:
    path - the path given as BioKIT.Path
    sg - the search graph
    scorer - the feature vector scorer
    fs - the feature sequence given as BioKIT.FeatureSequence
    borders - borders between different acitivities in the sequence
    name - the title of the plot (defaults to None)
    '''

    pp = PathPlot(path, fs, sg, scorer, borders)
    pp.plot()
    pp.pathax.set_xlim(left=0)
    return [pp.pathax, pp.fsax]


def plot_path(path, sg, scorer, name=None):
    '''
    plot a path object
    '''
    fig = plt.figure(name)
    pathax = fig.add_subplot(1, 1, 1)
    pathax = plotVitPath(path, sg, scorer, pathax)
    plt.tight_layout()
    return [pathax]

def plot_model(gaussianContainer, gaussMixture, name=None):
    plot_mixture(gaussMixture, name)

def plot_sequence(gmmset, modelnames, colormap='pink'):
    support, data = _get_mixture_values_of_sequence(gmmset, modelnames)
    fig = plt.figure()
    for dim in range(len(data)):
        pathax = fig.add_subplot(len(data), 1, dim + 1)
        extent = [0,1,support[dim][0], support[dim][-1]]
        pathax.imshow(numpy.atleast_2d(data[dim]), extent=extent,
                      aspect='auto', interpolation='nearest', cmap=colormap)

def _get_mixture_values_of_sequence(gmmset, modelnames, points=1000):
    """
    Plot a sequence of Gaussian mixture models (e.g. one HMM)

    Keyword arguments:
    gmmset - instance of GaussMixtureSet, must contain all named models
    modelnames - sequence of strings with model names
    """
    mixtures = [gmmset.getGaussMixture(gmmset.getModelId(m)) for m in modelnames]
    dimension = mixtures[0].getGaussianContainer().getDimensionality()
    support = [numpy.zeros((2, len(modelnames))) for x in range(dimension)]
    data = [numpy.zeros((points, len(modelnames))) for x in range(dimension)]

    #first pass to find the support limits
    for i, mixture in enumerate(mixtures):
        sup, mix_vals, comp_vals = _get_mixture_values(mixture, points=2)
        for dim in range(dimension):
            support[dim][:,i] = sup[dim]
    supportlimits = [(numpy.min(s[0,:]), numpy.max(s[1,:])) for s in support]
    #print("sup-lim: %s" % supportlimits)
    #second pass, get the actual values

    for i, mixture in enumerate(mixtures):
        sup, mix_vals, comp_vals = _get_mixture_values(mixture,
                                        supportlimits=supportlimits,
                                        points=points)
        for dim in range(dimension):
            data[dim][:,i] = mix_vals[dim]
    for dim in range(dimension):
        data[dim] = numpy.flipud(data[dim])
    return supportlimits, data


def _get_gmm_param(gaussMixture):
    """
    Return the parameters of a GMM (given as GaussMixture).

    Keyword arguments:
    gc - instance of GaussMixture

    Returns:
    a tuple of (nrgaussians, dimension, weights, meansbydim, covsbydim)
    """
    gc = gaussMixture.getGaussianContainer()
    nrgaussians = gc.getGaussiansCount()
    dimension = gc.getDimensionality()
    weights = gaussMixture.getMixtureWeights()
    meanlist = []
    covlist = []
    for i in range(nrgaussians):
        mean = gc.getMeanVector(i)
        covar = gc.getCovariance(i).getData()
        meanlist.append(mean)
        covlist.append(covar)
    #rearrange order of dimensions
    meansbydim = list(zip(*meanlist))
    covsbydim = list(zip(*covlist))
    return (nrgaussians, dimension, weights, meansbydim, covsbydim)

def _get_mixture_values(gaussMixture, supportlimits=None, points=1000):
    """
    Compute the values of a gaussian mixture and its individual components.

    Keyword arguments:
    gaussMixture - instance of GaussMixture
    support - support of each dimension given as list of (min,max) tuples
    points - number of points to evaluate

    Returns:
    Tuple of support, evaluated mixture and evaluated mixture components as
    list with each list item representing one dimension:
    (support, mixture_vals, component_vals)
    """
    nrgaussians, dimension, weights, meansbydim, covsbydim = _get_gmm_param(gaussMixture)
    mixture_vals = [numpy.zeros(points) for x in range(dimension)]
    component_vals = [numpy.zeros((nrgaussians, points)) for x in range(dimension)]
    support = []
    for dim in range(dimension):
        if supportlimits is None:
            meancov = list(zip(meansbydim[dim], covsbydim[dim]))
            lneg = [m - 3 * numpy.sqrt(v) for (m, v) in meancov]
            lpos = [m + 3 * numpy.sqrt(v) for (m, v) in meancov]
            bounds = lneg + lpos
            maxsup = max(bounds)
            minsup = min(bounds)
        else:
            minsup = supportlimits[dim][0]
            maxsup = supportlimits[dim][1]
        sup = numpy.linspace(minsup, maxsup, points)
        support.append(sup)
        for i in range(nrgaussians):
            y = weights[i] * normpdf(sup, meansbydim[dim][i],
                                     numpy.sqrt(covsbydim[dim][i]))
            mixture_vals[dim] += y
            component_vals[dim][i,:] = y
    assert len(mixture_vals) == len(component_vals)
    return (support, mixture_vals, component_vals)

def _get_mixture_values_of_path(path, gaussMixtureSet, supportlimits, points):
    """
    Compute the model mixture values along a path within given support limits.

    Keyword arguments:
    path - instance of Path
    gaussMixtureSet - instance of GaussMixtureSet
    supportlimits - list of (min,max) tuples for each feature dimension
    points - number of points to evaluate
    """
    dimension = len(supportlimits)
    data = [numpy.zeros((points, len(path))) for x in range(dimension)]
    for i, pi in enumerate(path):
        mixture = gaussMixtureSet.getGaussMixture(pi.mModelId)
        sup, mixture_val, comp_vals = _get_mixture_values(mixture, supportlimits, points)
        for dim in range(dimension):
            data[dim][:,i] = mixture_val[dim]
    for dim in range(dimension):
        data[dim] = numpy.flipud(data[dim])
    return data

def plot_mixture(gaussMixture, name=None, style="line"):
    """
    Plot the PDFs of a gaussian mixture model.

    Currently assumes diagonal covariance matrices.

    Keyword arguments:
    gaussMixture - the mixture to plot (instance of GaussMixture)
    style - either "line" or "intensitymap"
    """
    support, mixture_vals, component_vals = _get_mixture_values(gaussMixture)
    fig = plt.figure(name)
    dimension = len(mixture_vals)
    nrgaussians = component_vals[0].shape[0]
    for dim in range(dimension):
        pathax = fig.add_subplot(dimension, 1, dim + 1)
        for i in range(nrgaussians):
            if style=="line":
                pathax.plot(support[dim], component_vals[dim][i,:], 'b')
        if style=="line":
            pathax.plot(support[dim], mixture_vals[dim], 'r')
        elif style=="intensitymap":
            extent = [support[dim][0], support[dim][-1], 0, 1]
            pathax.imshow(numpy.atleast_2d(mixture_vals[dim]), extent=extent, aspect='auto')
        else:
            raise InvalidArgumentException("style %s not known" % style)


def show():
    """
    Show plotted figures on screen and block program execution
    """
    if PLOTTARGET is None:
        plt.show()
    else:
        plt.savefig("plot." + PLOTTARGET)


def posteriorgram(feature_vector_scorer, feature_sequence):
    """
    Plot a posteriorgram for a feature sequence

    Args:
        feature_vector_scorer: AbstractFeatureVectorScorer
        feature_sequence: FeatureSequence

    """
    model_names = sorted(feature_vector_scorer.getAvailableModelNames())
    model_ids = [feature_vector_scorer.getModelIdFromString(name) for name in model_names]

    # calculate scores
    scores = numpy.zeros((len(model_ids), len(feature_sequence)))
    for f_idx, feature_vector in enumerate(feature_sequence):
        for m_idx, model_id in enumerate(model_ids):
            scores[m_idx, f_idx] = feature_vector_scorer.score(model_id, feature_vector)

    # make plot
    plt.imshow(scores, aspect="auto", vmin=0)
    plt.xlabel("Time (feature vectors)")
    plt.ylabel("Models")
    plt.yticks(numpy.arange(len(model_names)),
               model_names)

    plt.colorbar()
    plt.tight_layout()
