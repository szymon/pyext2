from __future__ import annotations

import logging
import math
import struct

from typing import Optional, BinaryIO, Any

from bitarray import bitarray

from .inode import Inode, DirEntry
from .parser import SuperBlockInfo, BlockGroupDescriptionInfo


class SuperBlock:
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


class BlockGroupDescription:
    def __init__(self, data: bytes):
        info = BlockGroupDescriptionInfo(data)
        self.block_bitmap_id = info.bg_block_bitmap
        self.inode_bitmap_id = info.bg_inode_bitmap
        self.inode_table_id = info.bg_inode_table


class BlockBitmap:
    def __init__(self, data: bytes):
        self.data = bitarray()
        self.data.frombytes(data)

    def __getitem__(self, idx: int) -> Any:
        return self.data[idx]

    def __len__(self) -> int:
        return len(self.data)


class InodeBitmap:
    def __init__(self, data: bytes):
        self.data = bitarray()
        self.data.frombytes(data)

    def __getitem__(self, idx: int) -> Any:
        return self.data[idx]

    def __len__(self) -> int:
        return len(self.data)


class Ext2Reader:
    def __init__(self, ext_file: BinaryIO):
        self._file = ext_file

    def _seek(self, offset: int) -> None:
        self._file.seek(offset)

    def _read(self, size: int, offset: Optional[int] = None) -> bytes:

        if offset is not None:
            self._seek(offset)

        logging.debug("reading %d bytes at loc %d", size, self._file.tell())
        return self._file.read(size)

    def parse(self) -> None:
        self.superblock = SuperBlock(self._read(1024, offset=1024))

        assert self.superblock.nb_block_groups == 1
        # print(self.superblock)

        block_size = self.block_size = self.superblock.block_size

        block_group_desc_table = BlockGroupDescription(self._read(32, offset=block_size))

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

                if inode_index != 2 and inode_index < 11:
                    continue

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
                    buffer = bytes()
                    remaining_size = inode.size
                    for b in inode.block:
                        size = min(remaining_size, block_size)
                        remaining_size -= size
                        buffer += self._read(size, offset=b * block_size)
                    inode.raw_data = buffer

                self.inode_table = inode_table
