# import deprecation

class Reportable():
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.reporters = []

    # @deprecation.deprecated(details="Reportable will be removed in favor of stdlib logging")
    def register_reporter(self, reporter_fn):
        self.reporters.append(reporter_fn)

    def _report(self, **kwargs):
        for reporter in self.reporters:
            reporter(**kwargs)