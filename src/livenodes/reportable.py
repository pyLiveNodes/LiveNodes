class Reportable():
    def __init__(self):
        super().__init__()
        self.reporters = []

    def register_reporter(self, reporter_fn):
        self.reporters.append(reporter_fn)

    def _report(self, **kwargs):
        for reporter in self.reporters:
            reporter(**kwargs)
