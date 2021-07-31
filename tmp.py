import struct

offset = 2125824


def read_entries(data, n):
    i = 0
    of = 0
    while i < n:
        i += 1

        (mode, size, name_len, type_) = struct.unpack("IHbb", data[offset + of : offset + of + 8])
        if size == 0:
            size = 4096
        name = struct.unpack(f"{name_len}s", data[offset + of + 8 : offset + of + 8 + name_len])
        print(
            offset + of,
            mode,
            size,
            name_len,
            type_,
            name,
            data[offset + of : offset + of + 8 + name_len],
            sep="\t",
        )
        of += size


with open("ext2.img", "rb") as f_:
    data = f_.read()

read_entries(data, 20)
