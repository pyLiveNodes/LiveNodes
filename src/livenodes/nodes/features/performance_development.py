import numpy as np
from features.statistical import entropy

# How to use line profiling
# 1. add @profiles where you want to see line profiling
# 2. add function calls and imports here
# 3. on terminal: kernprof -l -v performance_development.py

if __name__ == "__main__":
    windows = 2
    channels = 15
    samples = 50
    totalSize = windows * channels * samples

    wts_flat = np.random.rand(windows * channels * samples) - 0.5
    wts_rand = wts_flat.reshape((windows, channels, samples))

    print('Nr Windows: %s, Nr Channels: %s, Nr Values: %s' %
          (windows, channels, samples))

    entropy(wts_flat)
