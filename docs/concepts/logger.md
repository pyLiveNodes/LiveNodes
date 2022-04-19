# Logger

there is a logger module.
each node is automatically hooked up to it and may be called using self._warn, self._log etc.
there are multiple levels of verbosity ie, error, warn, information, debug, verbose.

logs are printed out in dev modes, in the gui application they are automatically redirected into a file.