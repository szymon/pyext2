


1. parse superblock
    Starts at offset 1024 of the first group (or at the same offset from the
    start of ext2 image) with the size of 1024 bytes.

2. determine the numer of groups (ceil(s_blocks_count / s_blocks_per_group))

3. parse block group descriptor table
    each block group descriptor contains important information about that
    group

4. 
