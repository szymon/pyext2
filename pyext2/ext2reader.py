import enum
import io
import logging
import math
import pprint
import struct
from dataclasses import dataclass
from datetime import datetime

from bitstring import BitArray


def _debug_lines(lines):
    for line in lines:
        logging.debug(line)


def _pprint(data):
    buffer = io.StringIO()
    pprint.pprint(data, stream=buffer, sort_dicts=False)
    buffer.seek(0)
    return [x.rstrip() for x in buffer.readlines()]


def _parse(spec, data):
    obj = {}
    for line in spec.strip().splitlines():
        line = line.strip()
        if line.startswith("--"):
            continue

        offset, size, name = line.split("\t")

        field_type = {
            "1": "b",
            "3": "3b",
            "2": "H",
            "4": "I",
            "12": "12s",
            "16": "16s",
            "64": "64s",
            "4 x 4": "4I",
            "15 x 4": "15I",
            "0-255": "255s",
        }[size]

        if size == "4 x 4":
            size = str(4 * 4)

        elif size == "15 x 4":
            size = str(15 * 4)

        elif size == "0-255":
            size = str(255 * 4)

        size = int(size)
        offset = int(offset)

        value = struct.unpack(f"{field_type}", data[offset : offset + size])

        if len(value) == 1:
            value = value[0]

        obj[name] = value

    return obj


@dataclass
class DirEntry:
    index: int
    inode_type: int
    name: str


class SuperBlock:

    __spec = """
    0	4	s_inodes_count
    4	4	s_blocks_count
    8	4	s_r_blocks_count
    12	4	s_free_blocks_count
    16	4	s_free_inodes_count
    20	4	s_first_data_block
    24	4	s_log_block_size
    28	4	s_log_frag_size
    32	4	s_blocks_per_group
    36	4	s_frags_per_group
    40	4	s_inodes_per_group
    44	4	s_mtime
    48	4	s_wtime
    52	2	s_mnt_count
    54	2	s_max_mnt_count
    56	2	s_magic
    58	2	s_state
    60	2	s_errors
    62	2	s_minor_rev_level
    64	4	s_lastcheck
    68	4	s_checkinterval
    72	4	s_creator_os
    76	4	s_rev_level
    80	2	s_def_resuid
    82	2	s_def_resgid
    -- EXT2_DYNAMIC_REV Specific --
    84	4	s_first_ino
    88	2	s_inode_size
    90	2	s_block_group_nr
    92	4	s_feature_compat
    96	4	s_feature_incompat
    100	4	s_feature_ro_compat
    104	16	s_uuid
    120	16	s_volume_name
    136	64	s_last_mounted
    200	4	s_algo_bitmap
    -- Performance Hints --
    204	1	s_prealloc_blocks
    205	1	s_prealloc_dir_blocks
    206	2	(alignment)
    -- Journaling Support --
    208	16	s_journal_uuid
    224	4	s_journal_inum
    228	4	s_journal_dev
    232	4	s_last_orphan
    -- Directory Indexing Support --
    236	4 x 4	s_hash_seed
    252	1	s_def_hash_version
    253	3	padding - reserved for future expansion
    -- Other options --
    256	4	s_default_mount_options
    260	4	s_first_meta_bg
    """

    def __init__(self, data):
        self.data = data = _parse(self.__spec, data)

        self.blocks_count = data["s_blocks_count"]
        self.blocks_per_group = data["s_blocks_per_group"]

        self.log_block_size = data["s_log_block_size"]
        self.inode_size = data["s_inode_size"]
        self.block_size = 1024 << self.log_block_size
        self.inodes_per_block = int(self.block_size / self.inode_size)
        self.inodes_per_group = data["s_inodes_per_group"]
        self.inode_table_size = int(data["s_inodes_per_group"] / self.inodes_per_block)

        self.nb_block_groups = int(math.ceil(self.blocks_count / self.blocks_per_group))

    def __repr__(self):
        lines = ["SuperBlock"]

        lines.append(f"{self.blocks_count = }")
        lines.append(f"{self.blocks_per_group = }")
        lines.append(f"{self.nb_block_groups = }")
        lines.append(f"{self.log_block_size = }")
        lines.append(f"{self.inode_size = }")
        lines.append(f"{self.block_size = }")
        lines.append(f"{self.inodes_per_block = }")

        lines.extend(_pprint(self.data))

        return "\n\t".join(lines)


class BlockGroupDescription:
    __spec = """
    0	4	bg_block_bitmap
    4	4	bg_inode_bitmap
    8	4	bg_inode_table
    12	2	bg_free_blocks_count
    14	2	bg_free_inodes_count
    16	2	bg_used_dirs_count
    18	2	bg_pad
    20	12	bg_reserved
    """

    def __init__(self, data):
        self.data = data = _parse(self.__spec, data)
        self.block_bitmap_id = data["bg_block_bitmap"]
        self.inode_bitmap_id = data["bg_inode_bitmap"]
        self.inode_table_id = data["bg_inode_table"]

    def __repr__(self):
        lines = ["BlockGroupDescription"]

        lines.append(f"{self.block_bitmap_id = }")
        lines.append(f"{self.inode_bitmap_id = }")
        lines.append(f"{self.inode_table_id = }")

        # lines.extend(_pprint(self.data))

        return "\n\t".join(lines)


class BlockBitmap:
    def __init__(self, data):
        self.data = BitArray(data)


class InodeBitmap:
    def __init__(self, data):
        self.data = BitArray(data)

    def __getitem__(self, idx):
        return self.data[idx]

    def __len__(self):
        return len(self.data)


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

    __spec = """
    0	2	i_mode
    2	2	i_uid
    4	4	i_size
    8	4	i_atime
    12	4	i_ctime
    16	4	i_mtime
    20	4	i_dtime
    24	2	i_gid
    26	2	i_links_count
    28	4	i_blocks
    32	4	i_flags
    36	4	i_osd1
    40	15 x 4	i_block
    100	4	i_generation
    104	4	i_file_acl
    108	4	i_dir_acl
    112	4	i_faddr
    116	12	i_osd2
    """

    def __init__(self, data, log_block_size):
        self.data = data = _parse(self.__spec, data)

        # sys.stdout.buffer.write(b"\x41\x41\x41\x41" + data + b"\x42\x42\x42\x42")

        self.mode = InodeMode(data["i_mode"])
        self.flags = InodeFlags(data["i_flags"])

        self.block_index = int(data["i_blocks"] / (1 << log_block_size))

        self.size = data["i_size"]
        self.uid = data["i_uid"]
        self.gid = data["i_gid"]

        self._atime = datetime.fromtimestamp(data["i_atime"])
        self._ctime = datetime.fromtimestamp(data["i_ctime"])
        self._mtime = datetime.fromtimestamp(data["i_mtime"])
        self._dtime = datetime.fromtimestamp(data["i_dtime"])

        self.links_count = data["i_links_count"]
        self.blocks = data["i_blocks"]
        self.block = data["i_block"]

        self.files: dict[str, DirEntry] = {}
        self.raw_data = bytes()

    @property
    def is_file(self):
        return self.mode & InodeMode.EXT2_S_IFREG != 0

    @property
    def is_dir(self):
        return self.mode & InodeMode.EXT2_S_IFDIR != 0

    @property
    def is_link(self):
        return self.mode & InodeMode.EXT2_S_IFLNK != 0

    @property
    def atime(self):
        return None if self._atime == datetime.fromtimestamp(0) else self._atime

    @property
    def ctime(self):
        return None if self._ctime == datetime.fromtimestamp(0) else self._ctime

    @property
    def mtime(self):
        return None if self._mtime == datetime.fromtimestamp(0) else self._mtime

    @property
    def dtime(self):
        return None if self._dtime == datetime.fromtimestamp(0) else self._dtime

    def __repr__(self):
        lines = ["InodeTable"]
        lines.append(f"{self.block_index = }")
        lines.append(f"{self.mode = }")
        lines.append(f"{self.uid = }")
        lines.append(f"{self.gid = }")
        lines.append(f"{self.size = }")
        lines.append(f"{self.atime = }")
        lines.append(f"{self.ctime = }")
        lines.append(f"{self.mtime = }")
        lines.append(f"{self.dtime = }")
        lines.append(f"{self.links_count = }")
        lines.append(f"{self.blocks = }")
        lines.append(f"{self.block = }")
        # lines.append(f"{}")
        # lines.append(f"{}")
        # lines.append(f"{}")
        lines.append(f"{self.is_file = }")
        lines.append(f"{self.is_dir = }")
        lines.append(f"{self.is_link = }")

        if self.files:
            for _, info in self.files.items():
                lines.append(f"\t{info}")

        if self.raw_data:
            lines.append(f"\t{self.raw_data}")

        # lines.extend(_pprint(self.data))

        return "\n\t".join(lines)


class DirInodeInfo:
    __spec = """
    0	4	inode
    4	2	rec_len
    6	1	name_len
    7	1	file_type
    8	0-255	name
    """

    def __init__(self, data):
        self.data = _parse(data)


class DataBlocks:
    def __init__(self, data):
        pass


class Ext2Reader:
    def __init__(self, ext_file):
        self._file = ext_file
        self._groups = []

    def read_file(self, filename):
        inode_index = self.find_inode_for_path(filename)

        data = self.read_data_from_inode(inode_index)

        return data

    def _seek(self, offset):
        self._file.seek(offset)

    def _read(self, size, offset=None):

        if offset is not None:
            self._seek(offset)

        logging.debug("reading %d bytes at loc %d", size, self._file.tell())
        return self._file.read(size)

    def find_inode_for_path(self, path):
        assert path.startswith("/"), "path must be absolute"
        path_parts = path.split("/")[1:]
        current_inode_idx = 2

        for p in path_parts:
            current_inode = self.inode_table[current_inode_idx]

            for name, entry in current_inode.files.items():
                if entry.name == p.encode():
                    current_inode_idx = entry.index
                    break

            else:
                raise RuntimeError(f"no {p} in {current_inode.files.keys()}")

        return current_inode_idx

    def read_data_from_inode(self, inode_index):
        inode = self.inode_table[inode_index]

        assert inode.is_file

        return inode.raw_data.decode()

    def parse(self):
        self.superblock = SuperBlock(self._read(1024, offset=1024))

        assert self.superblock.nb_block_groups == 1
        # print(self.superblock)

        block_size = self.block_size = self.superblock.block_size

        block_group_desc_table = BlockGroupDescription(self._read(32, offset=block_size))

        _debug_lines(repr(self.superblock).split("\n"))
        _debug_lines(repr(block_group_desc_table).split("\n"))

        inode_size = self.superblock.inode_size

        inode_table_index = block_group_desc_table.inode_table_id
        block_bitmap_offset = block_size * block_group_desc_table.block_bitmap_id
        inode_bitmap_offset = block_size * block_group_desc_table.inode_bitmap_id
        inode_table_offset = block_size * inode_table_index

        inode_table_size = self.superblock.inode_table_size
        inodes_per_block = int(block_size / inode_size)
        inode_blocks_per_group = int(self.superblock.inodes_per_group / inodes_per_block)

        logging.debug("Block bitmap offset %d (block)", block_group_desc_table.block_bitmap_id)
        logging.debug("Inode bitmap offset %d (block)", block_group_desc_table.inode_bitmap_id)
        logging.debug(
            "Inode table offset %d-%d (block)",
            inode_table_index,
            inode_table_index + inode_blocks_per_group - 1,
        )

        assert inode_table_size * inodes_per_block == self.superblock.inodes_per_group

        BlockBitmap(self._read(block_size, offset=block_bitmap_offset))
        inode_bitmap = InodeBitmap(self._read(block_size, offset=inode_bitmap_offset))

        inode_table = {}
        count = 0

        for i in range(inode_blocks_per_group):
            ith_block_offset = inode_table_offset + block_size * i

            for j in range(inodes_per_block):
                count += 1
                inode_index = i * inodes_per_block + j + 1

                if not inode_bitmap[inode_index]:
                    continue

                jth_inode_offset = ith_block_offset + inode_size * j

                inode = Inode(
                    self._read(inode_size, offset=jth_inode_offset), self.superblock.log_block_size
                )

                logging.debug("Adding inode with index: %d", inode_index)
                inode_table[inode_index] = inode

                if inode.is_dir:
                    for b in inode.block:
                        if b == 0:
                            continue

                        offset = b * block_size
                        while True:
                            (index, size, name_len, type_) = struct.unpack(
                                "IHbb", self._read(8, offset=offset)
                            )
                            if index == 0:
                                break
                            name = struct.unpack(
                                f"{name_len}s", self._read(name_len, offset=offset + 8)
                            )[0]
                            offset += size

                            entry = DirEntry(index, type_, name)

                            if name not in inode.files:
                                inode.files[name] = entry

                if inode.is_file:
                    if inode.size >= block_size:
                        logging.warning("File in multiple blocks")

                    if inode.size > 64:
                        inode.size = 64

                    data = self._read(inode.size, offset=inode.block[0] * block_size)
                    inode.raw_data = data

                _debug_lines(repr(inode).split("\n"))

                self.inode_table = inode_table

        # pprint.pprint(self.superblock.data, sort_dicts=False)
        # pprint.pprint(block_group_desc_table.data, sort_dicts=False)
        # pprint.pprint({k: v.data for k, v in inode_tables.items()}, sort_dicts=False)

        # pprint.pprint(block_bitmap.data)
        # pprint.pprint(inode_bitmap.data)
