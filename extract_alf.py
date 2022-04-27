# extract ALF file format
import os
import io
import struct

import lzss


def find_sys4ini_bin_path(inpath):
    if os.path.isfile(inpath):
        filename = os.path.basename(inpath)
        filename = filename.lower()
        if filename == 'sys4ini.bin':
            return inpath
    elif os.path.isdir(inpath):
        child_filename_list = os.listdir(inpath)
        for child_filename in child_filename_list:
            child_filepath = os.path.join(inpath, child_filename)
            retval = find_sys4ini_bin_path(child_filepath)
            if retval is not None:
                return retval


def process_sys4ini(inpath):
    infile = open(inpath, 'rb')
    # header format
    # - 240 bytes signature
    # - 60 bytes unknown data

    # read header
    header_signature_bs = infile.read(240)

    if len(header_signature_bs) != 240:
        raise Exception(f'failed to read header data len(header_signature_bs) = {len(header_signature_bs)}')

    header_unknown_bs = infile.read(60)
    if len(header_unknown_bs) != 60:
        raise Exception(f'failed to read header data len(header_unknown_bs) = {len(header_unknown_bs)}')

    # TODO what is this?
    # // Hack for addon archives
    # if (!memcmp(hdr.signature_title, "S4AC", 4)) {
    #     lseek(fd, 268, SEEK_SET);
    # }
    if header_signature_bs[0:4] == b'S4AC':
        infile.seek(268)
        # oh so we don't know what is in the unknown data section so different type of containers have different offsets

    table_of_content_buffer = read_section(infile)
    infile.close()

    # the first 4 bytes store the length of the table of content
    stream = io.BytesIO(table_of_content_buffer)
    table_of_content_length_bs = stream.read(4)
    if len(table_of_content_length_bs) != 4:
        raise Exception(f'table_of_content_length_bs length {len(table_of_content_length_bs)} != 4')
    table_of_content_length = struct.unpack('<I', table_of_content_length_bs)[0]
    # entry info data is stored after this in chunk of 256 bytes
    # the first few bytes are recognizable as the ALF file name
    # the remaining bytes are unknown for now
    expected_all_entry_info_length = table_of_content_length * 256
    all_entry_info_data_bs = stream.read(expected_all_entry_info_length)
    if len(all_entry_info_data_bs) != expected_all_entry_info_length:
        raise Exception(f'len(all_entry_info_data_bs) != expected_all_entry_info_length - {len(all_entry_info_data_bs)} != {expected_all_entry_info_length}')
    # split bytes into 256 byte chunks
    all_entry_info_data_list = [
        all_entry_info_data_bs[i*256:(i+1)*256]
        for i in range(table_of_content_length)
    ]

    # nope the first 64 bytes contains the file name with null terminator
    # after the null terminator the remaining bytes are unknown
    # the next 4 bytes supposedly store the archive_index
    # the next 4 bytes supposedly store the file_index
    # the next 4 bytes supposedly store the offset
    # the next 4 bytes supposedly store the length
    # I will call this structure ALF_ENTRY_INFO
    alf_entry_info_list = []
    for entry_info_data_bs in all_entry_info_data_list:
        filename_data_bs = entry_info_data_bs[0:64]
        filename_bs = get_alf_filename(filename_data_bs)
        archive_index, file_index, offset, length = struct.unpack('<4I', entry_info_data_bs[64:64+16])
        alf_entry_info_list.append({
            'filename_bs': filename_bs,
            'archive_index': archive_index,
            'file_index': file_index,
            'offset': offset,
            'length': length
        })

    # TODO


def get_alf_filename(filename_data_bs: bytes):
    result = b''
    for value in filename_data_bs:
        if value == 0:
            break
        result += bytes([value])

    return result


def read_section(infile: io.BufferedReader):
    # section header format
    # unsigned long original_length;
    # unsigned long original_length2; // why?
    # unsigned long length;
    # unsigned long may be uint32

    # read section header
    section_header_bs = infile.read(12)
    if len(section_header_bs) != 12:
        raise Exception(f'failed to read section header len(section_header_bs) = {len(section_header_bs)}')

    original_length, original_length2, length = struct.unpack('<3I', section_header_bs)

    section_content_bs = infile.read(length)
    if len(section_content_bs) != length:
        raise Exception(f'failed to read section content len(section_content_bs) = {len(section_content_bs)} expecting {length}')

    # TODO decompress with lzss
    decoded_section_content_bs = lzss.decode(io.BytesIO(section_content_bs))
    if len(decoded_section_content_bs) != original_length:
        raise Exception(f'decoded_section_content_bs length {len(decoded_section_content_bs)} not equal to original_length {original_length}')

    return decoded_section_content_bs


def main():
    pass


if __name__ == '__main__':
    main()
