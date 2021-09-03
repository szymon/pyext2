from __future__ import annotations

import math
import struct
from pathlib import Path

from typing import BinaryIO, Any, Optional

from bitarray import bitarray

from .inode import Inode, DirEntry
from .parser import SuperBlockInfo, BlockGroupDescriptionInfo


class SuperBlock:
    EXT2_BAD_INO = 1
    EXT2_ROOT_INO = 2
    EXT2_GOOD_OLD_FIRST_INO = 11

    def __init__(self, data: bytes):
        info = SuperBlockInfo(data)

        self.blocks_count = info.s_blocks_count
        self.blocks_per_group = info.s_blocks_per_group

        self.log_block_size = info.s_log_block_size
        self.inode_size = info.s_inode_size
        self.block_size = 1024 << self.log_block_size
        self.inodes_per_block = int(self.block_size / self.inode_size)
        self.inodes_per_group = info.s_inodes_per_group
        self.inode_table_size = int(info.s_inodes_per_group / self.inodes_per_block)

        self.nb_block_groups = int(math.ceil(self.blocks_count / self.blocks_per_group))

        self.first_inode = info.s_first_ino


class BlockGroupDescription:
    def __init__(self, data: bytes):
        info = BlockGroupDescriptionInfo(data)
        self.block_bitmap_id = info.bg_block_bitmap
        self.inode_bitmap_id = info.bg_inode_bitmap
        self.inode_table_id = info.bg_inode_table


class BlockBitmap:
    def __init__(self, data: bytes):
        self.data = bitarray(endian="little")
        self.data.frombytes(data)

    def __getitem__(self, idx: int | slice) -> Any:
        return self.data[idx]

    def __len__(self) -> int:
        return len(self.data)


class InodeBitmap:
    def __init__(self, data: bytes):
        self.data = bitarray(endian="little")
        self.data.frombytes(data)

    def __getitem__(self, idx: int | slice) -> Any:
        return self.data[idx]

    def __len__(self) -> int:
        return len(self.data)


# 1. load first superblock
# 2. load groups (first one for now)


class Group:
    def __init__(
        self, superblock: SuperBlock, group_desc: BlockGroupDescription, ext_file: BinaryIO
    ):
        self.superblock = superblock
        self.group_desc = group_desc

        self.block_size = block_size = superblock.block_size
        block_bitmap_offset = group_desc.block_bitmap_id * block_size
        inode_bitmap_offset = group_desc.inode_bitmap_id * block_size

        ext_file.seek(block_bitmap_offset)
        self.block_bitmap = BlockBitmap(ext_file.read(block_size))

        ext_file.seek(inode_bitmap_offset)
        self.inode_bitmap = InodeBitmap(ext_file.read(block_size))

        inode_table_offset = group_desc.inode_table_id * block_size
        inode_size = superblock.inode_size

        inode_blocks_per_group = superblock.inodes_per_group // superblock.inode_table_size

        self.inode_table: dict[int, Inode] = {}
        for i in range(inode_blocks_per_group):
            ith_block = inode_table_offset + block_size * i

            for j in range(superblock.inode_table_size):
                inode_index = i * superblock.inode_table_size + j + 1

                if not self.inode_bitmap[inode_index - 1]:
                    continue

                inode_offset = ith_block + j * inode_size
                ext_file.seek(inode_offset)
                inode = Inode(ext_file.read(inode_size), superblock.log_block_size)

                if inode_index != SuperBlock.EXT2_ROOT_INO and inode_index < superblock.first_inode:
                    self.inode_table[inode_index] = inode
                    continue

                if inode.is_dir:
                    for b in inode.block:
                        if b == 0:
                            continue

                        offset = b * block_size
                        files: dict[str, DirEntry] = {}
                        while True:
                            ext_file.seek(offset)
                            (index, size, name_len, inode_type) = struct.unpack(
                                "IHbb", ext_file.read(8)
                            )
                            if index == 0:
                                break

                            name = struct.unpack(f"{name_len}s", ext_file.read(name_len))[0]
                            offset += size

                            entry = DirEntry(index, inode_type)

                            files[name.decode()] = entry

                            # size cannot be greater than 8 (header of dir entry)
                            #   + 255 (max name length)
                            if size > 255 + 8 + 1:
                                break

                    inode.set_files(files)

                self.inode_table[inode_index] = inode


class Ext2Reader:
    def __init__(self, file_path: str | Path):
        self.ext2_file_path = file_path

        with open(file_path, "rb") as ext_file:
            ext_file.seek(1024)
            self.superblock = SuperBlock(ext_file.read(1024))

            assert self.superblock.nb_block_groups == 1

            self.block_size = block_size = self.superblock.block_size

            self.group_description_table = []
            ext_file.seek(block_size)
            for _ in range(self.superblock.nb_block_groups):
                self.group_description_table.append(BlockGroupDescription(ext_file.read(32)))

            # XXX: this needs to be fixed if we want to support more than one group
            self.first_group = Group(self.superblock, self.group_description_table[0], ext_file)
            self.root_inode = self.first_group.inode_table[SuperBlock.EXT2_ROOT_INO]

    def _find_inode_for_path(self, inode: Inode, path: str, *, follow_links: bool = False) -> Inode:
        if path.startswith("/"):
            path = path[1:]

        path_parts = path.split("/")
        parent_inode = None

        if path_parts[0] == "":
            return inode

        for path_part in path_parts:
            assert path_part in inode.files.keys(), f"{path_part = } {inode.files.keys() = }"
            parent_inode = inode
            inode = self.first_group.inode_table[inode.files[path_part].index]

            if inode.is_link and follow_links:
                link_path = inode.get_link_path()
                inode = self._find_inode_for_path(
                    parent_inode, link_path, follow_links=follow_links
                )

        return inode

    def _read_data_for_inode(self, inode: Inode) -> bytes:
        remaining_size = inode.size
        data = bytes()

        assert remaining_size <= self.block_size

        with open(self.ext2_file_path, "rb") as ext_file:
            for b in inode.block:
                if b == 0:
                    break

                ext_file.seek(self.block_size * b)
                size_to_read = min(remaining_size, self.block_size)
                remaining_size -= size_to_read
                data += ext_file.read(size_to_read)

        return data

    def aa(self):
        print(self)

    def ls_command(self, path: str) -> None:
        inode = self._find_inode_for_path(self.root_inode, path, follow_links=True)
        assert not inode.is_file, "Can only `ls` directory inodes"

        print(list(inode.files.keys()))

    def cat_command(self, path: str) -> None:
        inode = self._find_inode_for_path(self.root_inode, path, follow_links=True)

        assert inode.is_file, "Can only `cat` file inodes"

        print(self._read_data_for_inode(inode).decode(), end="")

    def inode_info_command(
        self, *, path: Optional[str] = None, index: Optional[int] = None, follow_links: bool = False
    ) -> None:
        assert path is None or index is None

        if path is not None:
            inode = self._find_inode_for_path(self.root_inode, path, follow_links=follow_links)
        else:
            assert index is not None
            inode = self.first_group.inode_table[index]

        print(inode)
