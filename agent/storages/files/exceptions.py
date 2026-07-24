class StorageError(Exception):
    pass


class StorageKeyError(StorageError, ValueError):
    pass


class StorageObjectNotFoundError(StorageError, FileNotFoundError):
    pass
