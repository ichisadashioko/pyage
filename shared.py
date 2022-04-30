import io
import struct

import lzss


def read_lzss_section(infile: io.BufferedReader):
    # AGE engine pack data with 12 bytes header and followed by LZSS compressed data.
    # header format
    # unsigned long original_length;
    # unsigned long original_length2; // why?
    # unsigned long length;

    # read section header
    section_header_bs = infile.read(12)
    if len(section_header_bs) != 12:
        raise Exception(f'failed to read section header len(section_header_bs) = {len(section_header_bs)}')

    original_length, original_length2, length = struct.unpack('<3I', section_header_bs)

    # if original_length == length the data is not compressed
    if original_length != length:
        section_content_bs = infile.read(length)
        if len(section_content_bs) != length:
            raise Exception(f'failed to read section content len(section_content_bs) = {len(section_content_bs)} expecting {length}')

        # decompress with lzss
        decoded_section_content_bs = lzss.decode(io.BytesIO(section_content_bs))
        if len(decoded_section_content_bs) != original_length:
            raise Exception(f'decoded_section_content_bs length {len(decoded_section_content_bs)} not equal to original_length {original_length}')

        return decoded_section_content_bs
    else:
        bs = infile.read(length)
        if len(bs) != length:
            raise Exception(f'failed to read section content len(bs) = {len(bs)} expecting {length}')
        return infile.read(length)


AGF_TYPE_24BIT = 1
AGF_TYPE_32BIT = 2


def parse_agf_bitmap_header_bs(bitmap_header_bs: bytes):
    # typedef struct tagBITMAPFILEHEADER {
    #         WORD    bfType;
    #         DWORD   bfSize;
    #         WORD    bfReserved1;
    #         WORD    bfReserved2;
    #         DWORD   bfOffBits;
    # } BITMAPFILEHEADER

    # typedef struct tagBITMAPINFOHEADER{
    #         DWORD      biSize;
    #         LONG       biWidth;
    #         LONG       biHeight;
    #         WORD       biPlanes;
    #         WORD       biBitCount;
    #         DWORD      biCompression;
    #         DWORD      biSizeImage;
    #         LONG       biXPelsPerMeter;
    #         LONG       biYPelsPerMeter;
    #         DWORD      biClrUsed;
    #         DWORD      biClrImportant;
    # } BITMAPINFOHEADER

    # typedef struct tagRGBQUAD {
    #         BYTE    rgbBlue;
    #         BYTE    rgbGreen;
    #         BYTE    rgbRed;
    #         BYTE    rgbReserved;
    # } RGBQUAD;

    # WORD - 2 bytes - uint16
    # DWORD - 4 bytes - uint32
    # LONG - 4 bytes - int32

    # we need to parse these 3 structs

    if len(bitmap_header_bs) < (14 + 2 + 40 + 2):
        raise Exception(f'AGF bitmap header length is too short - {len(bitmap_header_bs)}')

    ####################################################################
    # BITMAPFILEHEADER
    bitmap_file_header_bs = bitmap_header_bs[0:14]
    bfType, bfSize, bfReserved1, bfReserved2, bfOffBits = struct.unpack('<HIHHI', bitmap_file_header_bs)
    bitmap_file_header = {
        'bfType': bfType,
        'bfSize': bfSize,
        'bfReserved1': bfReserved1,
        'bfReserved2': bfReserved2,
        'bfOffBits': bfOffBits
    }
    ####################################################################
    # after the BITMAPFILEHEADER we have 2 bytes probably for padding
    # BITMAPINFOHEADER

    # /* constants for the biCompression field */
    # #define BI_RGB        0L
    # #define BI_RLE8       1L
    # #define BI_RLE4       2L
    # #define BI_BITFIELDS  3L
    # #define BI_JPEG       4L
    # #define BI_PNG        5L

    bitmap_info_header_bs = bitmap_header_bs[16:16+40]
    # {
    #     'biSize': bitmap_info_header_bs[0:4],
    #     'biWidth': bitmap_info_header_bs[4:8],
    #     'biHeight': bitmap_info_header_bs[8:12],
    #     'biPlanes': bitmap_info_header_bs[12:14],
    #     'biBitCount': bitmap_info_header_bs[14:16],
    #     'biCompression': bitmap_info_header_bs[16:20],
    #     'biSizeImage': bitmap_info_header_bs[20:24],
    #     'biXPelsPerMeter': bitmap_info_header_bs[24:28],
    #     'biYPelsPerMeter': bitmap_info_header_bs[28:32],
    #     'biClrUsed': bitmap_info_header_bs[32:36],
    #     'biClrImportant': bitmap_info_header_bs[36:40],
    # }

    biSize, biWidth, biHeight, biPlanes, biBitCount, biCompression, biSizeImage, biXPelsPerMeter, biYPelsPerMeter, biClrUsed, biClrImportant = struct.unpack('<I2i2H2I2i2I', bitmap_info_header_bs)
    bitmap_info_header = {
        'biSize': biSize,
        'biWidth': biWidth,
        'biHeight': biHeight,
        'biPlanes': biPlanes,
        'biBitCount': biBitCount,
        'biCompression': biCompression,
        'biSizeImage': biSizeImage,
        'biXPelsPerMeter': biXPelsPerMeter,
        'biYPelsPerMeter': biYPelsPerMeter,
        'biClrUsed': biClrUsed,
        'biClrImportant': biClrImportant,
    }
    ####################################################################
    # RGBQUAD
    # if this image is 32 bit, then we have to parse the RGBQUAD
    # if this image is 24 bit, then we probably don't have to parse the RGBQUAD
    # ~~after the BITMAPINFOHEADER we have 2 bytes probably for padding or as a separator~~
    # the remaining bytes are probably RGBQUAD array
    # rgb_quad_array_bs = bitmap_header_bs[14+2+40+2:]
    rgb_quad_array_bs = bitmap_header_bs[14+2+40:]
    rgb_quad_array_bs_len = len(rgb_quad_array_bs)
    if (rgb_quad_array_bs_len % 4) != 0:
        raise Exception(f'(rgb_quad_array_bs_len % 4) != 0 - {rgb_quad_array_bs_len}')

    # TODO parse RGBQUAD array
    # we probably only need to parse RGBQUAD array if the image is 32 bit
    ####################################################################
    return {
        'BITMAPFILEHEADER': bitmap_file_header,
        'BITMAPINFOHEADER': bitmap_info_header,
        'RGBQUAD': rgb_quad_array_bs,
    }
