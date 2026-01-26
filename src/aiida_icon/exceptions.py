class SinglefileRestartNotImplementedError(Exception):
    def __init__(self):
        super().__init__("AiiDA-ICON currently only supports multifile restart files.")


class RemoteModelNamelistInaccessibleError(Exception):
    def __init__(self, msg: str = ""):
        super().__init__(f"One or more model namelists were given as remote paths and could not be read ({msg}).")
