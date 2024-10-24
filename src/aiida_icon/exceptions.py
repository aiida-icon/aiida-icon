class SinglefileRestartNotImplementedError(Exception):
    def __init__(self):
        super().__init__("AiiDA-ICON currently only supports multifile restart files.")
