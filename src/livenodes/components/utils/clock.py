class Clock():

    def __init__(self, node_id):
        self.__ctr = 0
        self.__node_id = node_id

    @property
    def state(self):
        return self.__node_id, self.__ctr

    @property
    def ctr(self):
        return self.__ctr

    def tick(self):
        self.__ctr += 1
        return self.ctr
