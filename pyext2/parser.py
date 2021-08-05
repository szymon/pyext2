import struct


class _Parser:
    def __init__(self, buffer: bytes, size: int):
        assert size == len(buffer), f"expected buffer of size {size}, was {len(buffer)}"
        self.buffer = buffer
        self.offset = 0

    def _read(self, format_string: str, size: int) -> tuple:
        data = struct.unpack(format_string, self.buffer[self.offset : self.offset + size])
        self.offset += size
        return data

    def read_u(self) -> int:
        data = self._read("I", 4)  # type: tuple[int, ...]
        assert isinstance(data, tuple) and len(data) == 1
        return data[0]

    def read_us(self, *, count: int = 1) -> tuple[int, ...]:
        return self._read(f"{count}I", 4 * count)

    def read_i(self) -> int:
        data = self._read("i", 4)  # type: tuple[int, ...]
        assert isinstance(data, tuple) and len(data) == 1
        return data[0]

    def read_is(self, *, count: int = 1) -> tuple[int, ...]:
        return self._read(f"{count}i", 4 * count)

    def read_s(self) -> int:
        data = self._read("h", 2)  # type: tuple[int, ...]
        assert isinstance(data, tuple) and len(data) == 1
        return data[0]

    def read_ss(self, *, count: int = 1) -> tuple[int, ...]:
        return self._read(f"{count}h", 2 * count)

    def read_b(self) -> int:
        data = self._read("b", 1)  # type: tuple[int, ...]
        assert isinstance(data, tuple) and len(data) == 1
        return data[0]

    def read_bs(self, *, count: int = 1) -> tuple[int, ...]:
        return self._read(f"{count}b", 1 * count)

    def read_string(self, length: int) -> bytes:
        # vvv make mypy happy
        data = self._read(f"{length}s", length)  # type: tuple[bytes, ...]

        assert isinstance(data, tuple) and len(data) == 1

        return data[0]


class SuperBlockInfo(_Parser):
    __size__ = 1024

    def __init__(self, buffer: bytes):
        super().__init__(buffer, SuperBlockInfo.__size__)

        self.s_inodes_count = self.read_u()
        self.s_blocks_count = self.read_u()
        self.s_r_blocks_count = self.read_u()
        self.s_free_blocks_count = self.read_u()
        self.s_free_inodes_count = self.read_u()
        self.s_first_data_block = self.read_u()
        self.s_log_block_size = self.read_u()
        self.s_log_frag_size = self.read_u()
        self.s_blocks_per_group = self.read_u()
        self.s_frags_per_group = self.read_u()
        self.s_inodes_per_group = self.read_u()
        self.s_mtime = self.read_u()
        self.s_wtime = self.read_u()
        self.s_mnt_count = self.read_s()
        self.s_max_mnt_count = self.read_s()
        self.s_magic = self.read_s()
        self.s_state = self.read_s()
        self.s_errors = self.read_s()
        self.s_minor_rev_level = self.read_s()
        self.s_lastcheck = self.read_u()
        self.s_checkinterval = self.read_u()
        self.s_creator_os = self.read_u()
        self.s_rev_level = self.read_u()
        self.s_def_resuid = self.read_s()
        self.s_def_resgid = self.read_s()

        # EXT2_DYNAMIC_REV Specific
        self.s_first_ino = self.read_u()
        self.s_inode_size = self.read_s()
        self.s_block_group_nr = self.read_s()
        self.s_feature_compat = self.read_u()
        self.s_feature_incompat = self.read_u()
        self.s_feature_ro_compat = self.read_u()
        self.s_uuid = self.read_bs(count=16)
        self.s_volume_name = self.read_string(length=16)
        self.s_last_mounted = self.read_string(length=64)
        self.s_algo_bitmap = self.read_u()

        # Performance Hints
        self.s_prealloc_blocks = self.read_b()
        self.s_prealloc_dir_blocks = self.read_b()
        self.read_bs(count=2)  # alignment

        # Journaling Support
        self.s_journal_uuid = self.read_bs(count=16)
        self.s_journal_inum = self.read_u()
        self.s_journal_dev = self.read_u()
        self.s_last_orphan = self.read_u()

        # Directory Indexing Support
        self.s_hash_seed = self.read_us(count=4)
        self.s_def_hash_version = self.read_b()
        self.read_bs(count=3)  # padding

        # Other options
        self.s_default_mount_options = self.read_u()
        self.s_first_meta_bg = self.read_u()


class BlockGroupDescriptionInfo(_Parser):
    __size__ = 32

    def __init__(self, data: bytes):
        super().__init__(data, BlockGroupDescriptionInfo.__size__)

        self.bg_block_bitmap = self.read_u()
        self.bg_inode_bitmap = self.read_u()
        self.bg_inode_table = self.read_u()
        self.bg_free_blocks_count = self.read_s()
        self.bg_free_inodes_count = self.read_s()
        self.bg_used_dirs_count = self.read_s()


class InodeInfo(_Parser):
    __size__ = 128

    def __init__(self, data: bytes):
        super().__init__(data, InodeInfo.__size__)

        self.i_mode = self.read_s()
        self.i_uid = self.read_s()
        self.i_size = self.read_u()
        self.i_atime = self.read_u()
        self.i_mtime = self.read_u()
        self.i_ctime = self.read_u()
        self.i_dtime = self.read_u()
        self.i_gid = self.read_s()
        self.i_links_count = self.read_s()
        self.i_blocks = self.read_u()
        self.i_flags = self.read_u()
        self.i_osd1 = self.read_u()
        self.i_block = self.read_us(count=15)
        self.i_generation = self.read_u()
        self.i_file_acl = self.read_u()
        self.i_dir_acl = self.read_u()
        self.i_faddr = self.read_u()
        self.i_osd2 = self.read_bs(count=12)
