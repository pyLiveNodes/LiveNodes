import time 

class Clock():

    def __init__(self, node, should_time):
        self.ctr = 0
        self.times = []
        self.node = node

        if should_time:
            self.tick = self._tick_with_time
        else:
            self.tick = self._tick

    def _tick_with_time(self):
        self.ctr += 1
        self.times.append(time.time())
        return self.ctr

    def _tick(self):
        self.ctr += 1
        return self.ctr
