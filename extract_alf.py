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

    ####################################################################
    bs = stream.read(4)
    if len(bs) != 4:
        raise Exception(f'bs length {len(bs)} != 4')
    number_of_alf_files = struct.unpack('<I', bs)[0]
    ####################################################################
    # entry info data is stored after this in chunk of 256 bytes
    # the first few bytes are recognizable as the ALF file name
    # the remaining bytes are unknown for now
    expected_all_entry_info_length = number_of_alf_files * 256
    all_entry_info_data_bs = stream.read(expected_all_entry_info_length)
    if len(all_entry_info_data_bs) != expected_all_entry_info_length:
        raise Exception(f'len(all_entry_info_data_bs) != expected_all_entry_info_length - {len(all_entry_info_data_bs)} != {expected_all_entry_info_length}')
    # split bytes into 256 byte chunks
    all_entry_info_data_list = [
        all_entry_info_data_bs[i*256:(i+1)*256]
        for i in range(number_of_alf_files)
    ]

    alf_file_info_list = []
    for entry_info_data_bs in all_entry_info_data_list:
        alf_filename = trim_filename_data(entry_info_data_bs)
        alf_file_info_list.append({
            'name': alf_filename
        })
    ####################################################################
    # now we have the table of content and the list of ALF file names

    # read the number of archive entries
    bs = stream.read(4)
    if len(bs) != 4:
        raise Exception(f'failed to read number of archive entries len(bs) != 4 - {len(bs)}')
    number_of_archive_entries = struct.unpack('<I', bs)[0]
    ####################################################################
    archive_entry_info_list = []
    for i in range(number_of_archive_entries):
        # the first 64 bytes contains the file name with null terminator
        # after the null terminator the remaining bytes are unknown
        # the next 4 bytes supposedly store the archive_index
        # the next 4 bytes supposedly store the file_index
        # the next 4 bytes supposedly store the offset
        # the next 4 bytes supposedly store the length
        bs = stream.read(80)
        if len(bs) != 80:
            raise Exception(f'failed to read archive entry #{i} len(bs) != 80 - {len(bs)}')
        archive_entry_info_list.append({
            'name': trim_filename_data(bs[0:64]),
            'archive_index': struct.unpack('<I', bs[64:68])[0],
            'file_index': struct.unpack('<I', bs[68:72])[0],
            'offset': struct.unpack('<I', bs[72:76])[0],
            'length': struct.unpack('<I', bs[76:80])[0],
        })


def trim_filename_data(filename_data_bs: bytes):
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
