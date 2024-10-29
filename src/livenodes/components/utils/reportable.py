class Reportable():
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.reporters = []

    def register_reporter(self, reporter_fn):
        self.reporters.append(reporter_fn)

    def reporter_registered(self, reporter_fn):
        return reporter_fn in self.reporters

    def register_reporter_once(self, reporter_fn):
        if not self.reporter_registered(reporter_fn):
            self.reporters.append(reporter_fn)

    def deregister_reporter(self, reporter_fn):
        if not self.reporter_registered(reporter_fn):
            raise ValueError("Reporter function not found in list.")
        self.reporters.remove(reporter_fn)

    def _report(self, **kwargs):
        for reporter in self.reporters:
            reporter(**kwargs)