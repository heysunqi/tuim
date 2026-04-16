"""SFTP service for file transfer over SSH connections."""
from __future__ import annotations

import logging
import os
import stat
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, List, Optional

import asyncssh

from tuim.models import Connection

logger = logging.getLogger(__name__)


@dataclass
class FileEntry:
    """Represents a file or directory entry."""
    name: str           # file name
    full_path: str      # absolute path
    is_dir: bool        # whether it's a directory
    size: int           # size in bytes
    modified: str       # formatted modification time
    permissions: str    # "drwxr-xr-x" style


def _format_size(size):
    # type: (int) -> str
    """Format byte size to human-readable string."""
    if size < 1024:
        return "{}B".format(size)
    elif size < 1024 * 1024:
        return "{:.1f}K".format(size / 1024)
    elif size < 1024 * 1024 * 1024:
        return "{:.1f}M".format(size / (1024 * 1024))
    else:
        return "{:.1f}G".format(size / (1024 * 1024 * 1024))


def _format_time(ts):
    # type: (float) -> str
    """Format a Unix timestamp to a short date string."""
    try:
        dt = datetime.fromtimestamp(ts)
        now = datetime.now()
        if dt.year == now.year:
            return dt.strftime("%m-%d %H:%M")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return "-"


def _perm_string(mode):
    # type: (int) -> str
    """Convert a file mode to a drwxr-xr-x style string."""
    parts = []
    if stat.S_ISDIR(mode):
        parts.append("d")
    elif stat.S_ISLNK(mode):
        parts.append("l")
    else:
        parts.append("-")
    for who in ("USR", "GRP", "OTH"):
        r = "r" if mode & getattr(stat, "S_IR" + who) else "-"
        w = "w" if mode & getattr(stat, "S_IW" + who) else "-"
        x = "x" if mode & getattr(stat, "S_IX" + who) else "-"
        parts.append(r + w + x)
    return "".join(parts)


def list_local_dir(path):
    # type: (str) -> List[FileEntry]
    """List files in a local directory, returning FileEntry objects."""
    entries = []  # type: List[FileEntry]
    try:
        for item in os.scandir(path):
            try:
                st = item.stat(follow_symlinks=False)
                entries.append(FileEntry(
                    name=item.name,
                    full_path=item.path,
                    is_dir=item.is_dir(follow_symlinks=True),
                    size=st.st_size if not item.is_dir(follow_symlinks=True) else 0,
                    modified=_format_time(st.st_mtime),
                    permissions=_perm_string(st.st_mode),
                ))
            except PermissionError:
                entries.append(FileEntry(
                    name=item.name,
                    full_path=item.path,
                    is_dir=False,
                    size=0,
                    modified="-",
                    permissions="----------",
                ))
    except PermissionError:
        pass
    # Sort: directories first, then alphabetical
    entries.sort(key=lambda e: (not e.is_dir, e.name.lower()))
    return entries


class SFTPService:
    """SFTP client service wrapping asyncssh SFTP."""

    def __init__(self, connection):
        # type: (Connection) -> None
        self._connection = connection
        self._jump_conn = None  # type: Optional[asyncssh.SSHClientConnection]
        self._ssh_conn = None  # type: Optional[asyncssh.SSHClientConnection]
        self._sftp = None  # type: Optional[asyncssh.SFTPClient]

    async def connect(self):
        # type: () -> None
        """Establish SSH + SFTP connection, reusing SSHHandler's connect_kwargs pattern."""
        cfg = self._connection.ssh_config
        host = self._connection.host
        port = self._connection.port

        connect_kwargs = {
            "host": host,
            "port": port,
            "known_hosts": None,
        }

        if cfg is not None:
            if cfg.username:
                connect_kwargs["username"] = cfg.username
            if cfg.private_key_path:
                connect_kwargs["client_keys"] = [cfg.private_key_path]
            if cfg.password:
                connect_kwargs["password"] = cfg.password

        # If jump host is configured, establish tunnel first
        if cfg is not None and cfg.jump_host:
            jump_kwargs = {
                "host": cfg.jump_host,
                "port": cfg.jump_port,
                "known_hosts": None,
            }
            if cfg.jump_username:
                jump_kwargs["username"] = cfg.jump_username
            if cfg.jump_private_key_path:
                jump_kwargs["client_keys"] = [cfg.jump_private_key_path]
            if cfg.jump_password:
                jump_kwargs["password"] = cfg.jump_password
            self._jump_conn = await asyncssh.connect(**jump_kwargs)
            connect_kwargs["tunnel"] = self._jump_conn

        self._ssh_conn = await asyncssh.connect(**connect_kwargs)
        self._sftp = await self._ssh_conn.start_sftp_client()

    async def disconnect(self):
        # type: () -> None
        """Close SFTP and SSH connections."""
        if self._sftp is not None:
            self._sftp.exit()
            self._sftp = None
        if self._ssh_conn is not None:
            self._ssh_conn.close()
            try:
                await self._ssh_conn.wait_closed()
            except Exception:
                pass
            self._ssh_conn = None
        if self._jump_conn is not None:
            self._jump_conn.close()
            try:
                await self._jump_conn.wait_closed()
            except Exception:
                pass
            self._jump_conn = None

    async def get_home_dir(self):
        # type: () -> str
        """Get the remote user's home directory."""
        if self._sftp is None:
            return "/"
        try:
            cwd = await self._sftp.getcwd()
            return cwd if cwd else "/"
        except Exception:
            return "/"

    async def listdir(self, path):
        # type: (str) -> List[FileEntry]
        """List files in a remote directory."""
        if self._sftp is None:
            return []
        entries = []  # type: List[FileEntry]
        try:
            name_list = await self._sftp.readdir(path)
            for item in name_list:
                name = item.filename
                if name in (".", ".."):
                    continue
                full_path = path.rstrip("/") + "/" + name
                fa = item.attrs  # SFTPAttrs
                permissions = fa.permissions
                is_dir = stat.S_ISDIR(permissions) if permissions is not None else False
                size = fa.size if fa.size is not None and not is_dir else 0
                mtime = _format_time(fa.mtime) if fa.mtime is not None else "-"
                perms = _perm_string(permissions) if permissions is not None else "----------"
                entries.append(FileEntry(
                    name=name,
                    full_path=full_path,
                    is_dir=is_dir,
                    size=size,
                    modified=mtime,
                    permissions=perms,
                ))
        except PermissionError:
            pass
        entries.sort(key=lambda e: (not e.is_dir, e.name.lower()))
        return entries

    async def download(self, remote_path, local_path, progress_callback=None):
        # type: (str, str, Optional[Callable]) -> None
        """Download a remote file to a local path."""
        if self._sftp is None:
            raise RuntimeError("SFTP not connected")
        kwargs = {}
        if progress_callback is not None:
            kwargs["progress_handler"] = progress_callback
        await self._sftp.get(remote_path, local_path, **kwargs)

    async def upload(self, local_path, remote_path, progress_callback=None):
        # type: (str, str, Optional[Callable]) -> None
        """Upload a local file to a remote path."""
        if self._sftp is None:
            raise RuntimeError("SFTP not connected")
        kwargs = {}
        if progress_callback is not None:
            kwargs["progress_handler"] = progress_callback
        await self._sftp.put(local_path, remote_path, **kwargs)

    async def mkdir(self, remote_path):
        # type: (str) -> None
        """Create a directory on the remote server."""
        if self._sftp is None:
            raise RuntimeError("SFTP not connected")
        await self._sftp.mkdir(remote_path)
