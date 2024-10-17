class Reportable():
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.reporters = []

    def register_reporter(self, reporter_fn):
        self.reporters.append(reporter_fn)

    def deregister_reporter(self, reporter_fn):
        if reporter_fn in self.reporters:
            self.reporters.remove(reporter_fn)
        else:
            raise ValueError("Reporter function not found in list.")

    def _report(self, **kwargs):
        for reporter in self.reporters:
            reporter(**kwargs)