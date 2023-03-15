import ctypes
from ctypes import wintypes, windll
from pathlib import Path

def get_desktop():
    """
    Return the path to the desktop folder for the current user.
    This isn't ALWAYS the same as the user's home directory so we have to use ctypes to get the path.
    """
    buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH + 1)
    ctypes.windll.shell32.SHGetFolderPathW(None, 0x0010, None, 0, buf)
    return Path(buf.value)