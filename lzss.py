# decode lzss stream
import io

SIZE_OF_RING_BUFFER = 4096
UPPER_LIMIT_OF_MATCH_LENGTH = 18
THRESHOLD = 2


def decode(infile: io.BufferedReader):
    outfile = io.BytesIO()
    text_buffer = [32 for _ in range(SIZE_OF_RING_BUFFER + UPPER_LIMIT_OF_MATCH_LENGTH - 1)]

    # TODO rename this variable
    r = SIZE_OF_RING_BUFFER - UPPER_LIMIT_OF_MATCH_LENGTH
    # TODO split this flags into multiple variables with meaningful names
    flags = 0
    while True:
        flags = int(flags / 2)

        if (flags & 256) == 0:
            bs = infile.read(1)
            if len(bs) == 0:
                break
            c = bs[0]
            flags = c | 0xff00

        if (flags & 1):
            bs = infile.read(1)
            if len(bs) == 0:
                break
            c = bs[0]
            outfile.write(bytes([c]))
            text_buffer[r] = c
            r = (r + 1) % SIZE_OF_RING_BUFFER
        else:
            bs = infile.read(2)
            if len(bs) != 2:
                break
            i = bs[0]
            j = bs[1]
            i |= (j & 0xf0) << 4
            j = (j & 0x0f) + THRESHOLD
            for k in range(j+1):
                c = text_buffer[(i + k) % SIZE_OF_RING_BUFFER]
                outfile.write(bytes([c]))
                text_buffer[r] = c
                r = (r + 1) % SIZE_OF_RING_BUFFER

    return outfile.getvalue()
