import os
import tempfile

_fd, _path = tempfile.mkstemp(suffix=".db")
os.environ["DB_PATH"] = _path
os.close(_fd)

from app.database import init_db  # noqa: E402

init_db()
