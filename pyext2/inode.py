from __future__ import annotations

from dataclasses import dataclass
import enum

from .parser import InodeInfo


@dataclass
class DirEntry:
    index: int
    inode_type: int
    name: str


class InodeMode(enum.IntFlag):
    EXT2_S_IFSOCK = 0xC000
    EXT2_S_IFLNK = 0xA000
    EXT2_S_IFREG = 0x8000
    EXT2_S_IFBLK = 0x6000
    EXT2_S_IFDIR = 0x4000
    EXT2_S_IFCHR = 0x2000
    EXT2_S_IFIFO = 0x1000
    EXT2_S_ISUID = 0x0800
    EXT2_S_ISGID = 0x0400
    EXT2_S_ISVTX = 0x0200
    EXT2_S_IRUSR = 0x0100
    EXT2_S_IWUSR = 0x0080
    EXT2_S_IXUSR = 0x0040
    EXT2_S_IRGRP = 0x0020
    EXT2_S_IWGRP = 0x0010
    EXT2_S_IXGRP = 0x0008
    EXT2_S_IROTH = 0x0004
    EXT2_S_IWOTH = 0x0002
    EXT2_S_IXOTH = 0x0001


class InodeFlags(enum.IntFlag):
    EXT2_SECRM_FL = 0x00000001
    EXT2_UNRM_FL = 0x00000002
    EXT2_COMPR_FL = 0x00000004
    EXT2_SYNC_FL = 0x00000008
    EXT2_IMMUTABLE_FL = 0x00000010
    EXT2_APPEND_FL = 0x00000020
    EXT2_NODUMP_FL = 0x00000040
    EXT2_NOATIME_FL = 0x00000080
    EXT2_DIRTY_FL = 0x00000100
    EXT2_COMPRBLK_FL = 0x00000200
    EXT2_NOCOMPR_FL = 0x00000400
    EXT2_ECOMPR_FL = 0x00000800
    EXT2_BTREE_FL = 0x00001000
    EXT2_INDEX_FL = 0x00001000
    EXT2_IMAGIC_FL = 0x00002000
    EXT3_JOURNAL_DATA_FL = 0x00004000
    EXT2_RESERVED_FL = 0x80000000


class Inode:
    def __init__(self, data: bytes, log_block_size: int):
        info = InodeInfo(data)

        self.mode = InodeMode(info.i_mode)
        self.flags = InodeFlags(info.i_flags)

        self.block_index = int(info.i_blocks / (1 << log_block_size))

        self.size = info.i_size
        self.uid = info.i_uid
        self.gid = info.i_gid

        self.links_count = info.i_links_count
        self.blocks = info.i_blocks
        self.block = info.i_block

        self.files: dict[str, DirEntry] = {}
        self.raw_data = bytes()

    @property
    def is_file(self) -> bool:
        return self.mode & InodeMode.EXT2_S_IFREG != 0

    @property
    def is_dir(self) -> bool:
        return self.mode & InodeMode.EXT2_S_IFDIR != 0

    @property
    def is_link(self) -> bool:
        return self.mode & InodeMode.EXT2_S_IFLNK != 0
