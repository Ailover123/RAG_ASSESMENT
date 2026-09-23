import re
from pathlib import Path
from fastapi import Header, HTTPException, status

_SESSION_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")
_FILENAME_RE = re.compile(r"[^A-Za-z0-9._ -]+")


def get_session_id(x_session_id: str = Header(..., alias="X-Session-ID")) -> str:
    value = x_session_id.strip()
    if not _SESSION_RE.fullmatch(value):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A valid X-Session-ID header is required.")
    return value


def sanitize_filename(filename: str) -> str:
    name = Path(filename.replace("\\", "/")).name
    name = _FILENAME_RE.sub("_", name).strip(" .")
    if not name or name in {".", ".."}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file must have a valid filename.")
    stem, suffix = Path(name).stem[:100].strip(" ."), Path(name).suffix.lower()
    return f"{stem or 'document'}{suffix}"
