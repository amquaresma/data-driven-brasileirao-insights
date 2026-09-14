class BrasileiraoSourceError(Exception):
    """Erro genérico ao consumir a fonte campeonato-brasileiro-api."""

    def __init__(self, message: str, *, code: str | None = None, stderr: str | None = None):
        super().__init__(message)
        self.code = code
        self.stderr = stderr
