"""An OS lock is automatically released after crashes; no stale lock deletion needed."""
from contextlib import contextmanager
from pathlib import Path
import os

@contextmanager
def output_lock(root):
    Path(root).mkdir(parents=True,exist_ok=True)
    f=(Path(root)/'.operation.lock').open('a+b')
    try:
        if os.name=='nt':
            import msvcrt
            f.seek(0);f.write(b'0');f.flush();f.seek(0)
            try:msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
            except OSError:raise RuntimeError('Output in use: stop batch/review before opening another writer')
        else:
            import fcntl
            try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise RuntimeError('Output in use: stop batch/review before opening another writer')
        yield
    finally:f.close()
