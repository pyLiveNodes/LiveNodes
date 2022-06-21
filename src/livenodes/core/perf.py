from timeit import default_timer as timer
import numpy as np

class Abstract_Perf():
    def __init__(self):
        self.calls = []

    def call_fn(self, fn, *args, **kwargs):
        pass
    
    def average(self):
        return np.mean(self.calls[:1000])

    def average_total(self):
        return np.mean(self.calls)


class Time_Per_Call(Abstract_Perf):
    def call_fn(self, fn, *args, **kwargs):
        start = timer()
        res = fn(*args, **kwargs)
        self.calls.append(timer() - start)
        return res


class Time_Between_Call(Abstract_Perf):
    def __init__(self):
        super().__init__()
        self.last_time = None

    def call_fn(self, fn, *args, **kwargs):
        if self.last_time is not None:
            self.calls.append(timer() - self.last_time)
        self.last_time = timer()
        return fn(*args, **kwargs)
        