# load the pickle log and unpack all the assets
import os
import io
import time
import struct
import pickle
import argparse
import collections

import tqdm
import enlighten

import numpy as np
import cv2

import shared


IMAGE_OUTPUT_FORMAT_LIST = ['png', 'bmp', 'jpg']


def handle_agf_data(
    agf_content_bs: bytes,
):
    stream = io.BytesIO(agf_content_bs)

    # AGF header
    # 4 bytes: signature
    # 4 bytes: type
    # 4 bytes: unknown
    bs = stream.read(12)
    if len(bs) != 12:
        raise Exception(f'AGF header is not 12 bytes long - {len(bs)}')

    signature_bs = bs[0:4]
    agf_type = struct.unpack('<I', bs[4:8])[0]
    if agf_type not in [AGF_TYPE_24BIT, AGF_TYPE_32BIT]:
        print('signature_bs', signature_bs)
        print('agf_type', agf_type)
        raise Exception(f'AGF unknown type {agf_type}')

    bitmap_header_bs = shared.read_lzss_section(stream)
    bitmap_header = shared.parse_agf_bitmap_header_bs(bitmap_header_bs)
    image_data_bs = shared.read_lzss_section(stream)

    bitmap_info_header = bitmap_header['BITMAPINFOHEADER']
    biWidth = bitmap_info_header['biWidth']
    biHeight = bitmap_info_header['biHeight']
    biBitCount = bitmap_info_header['biBitCount']
    rgb_quad_array_bs = bitmap_header['RGBQUAD']
    tmp_np_array = np.frombuffer(rgb_quad_array_bs, dtype=np.uint8)
    rgb_quad_array = tmp_np_array.reshape((-1, 4))
    biClrUsed = bitmap_info_header['biClrUsed']

    # getting image data directly from the array
    image_data_bs_len = len(image_data_bs)
    image_data_bs_len == int(biWidth * biHeight * bytes_per_pixel)
    tmp_np_array = np.frombuffer(image_data_bs, dtype=np.uint8)
    bgr_image = tmp_np_array.reshape((biHeight, biWidth, bytes_per_pixel))
    reorder_bgr_image = np.flipud(bgr_image)
    rgb_image = cv2.cvtColor(reorder_bgr_image, cv2.COLOR_BGR2RGB)

    # mapping with RGBQUAD
    image_data_array = np.array([rgb_quad_array[i] for i in image_index_array])

    # merging transparency
    acif_header_bs = stream.read(24)
    transparency_data_bs = shared.read_lzss_section(stream)
    number_of_channels = bgr_image.shape[2]

    # merge the transparency array with the image data
    tmp_np_array = np.frombuffer(transparency_data_bs, dtype=np.uint8)
    transparency_array = tmp_np_array.reshape((biHeight, biWidth, 1))

    bgra_image = np.concatenate((reorder_bgr_image, transparency_array), axis=2)
    rgba_image = cv2.cvtColor(bgra_image, cv2.COLOR_BGRA2RGBA)


def handle_single_alf_file(
    filepath: str,
    archive_list: list,
):
    with open(filepath, mode='rb') as alf_infile:
        number_of_archive_entries = len(archive_list)
        enlighten_counter = enlighten.Counter(total=number_of_archive_entries)

        for archive_index in range(number_of_archive_entries):
            try:
                archive_info = archive_list[archive_index]

                filename_bs = archive_info['name']
                filename = filename_bs.decode('ascii')
                ext = os.path.splitext(filename)[1]
                ext = ext.lower()
                if not ext == '.agf':
                    enlighten_counter.update()
                    continue

                offset = agf_archive_info['offset']
                length = agf_archive_info['length']
                alf_infile.seek(offset)
                agf_content_bs = alf_infile.read(length)

                handle_agf_data(agf_content_bs)
            except Exception as ex:
                stack_trace = traceback.format_exc()
                print(f'{shared.FG_RED}ERROR: Error occurs while processing archive_info index {archive_index}{shared.RESET_COLOR}')
                print(stack_trace)
                print(ex)

            enlighten_counter.update()


def handle_metadata_info_obj(
    metadata_info: dict,
):
    metadata_filepath = metadata_info['path']
    metadata_parent, metadata_filename = os.path.split(metadata_filepath)

    alf_file_info_list = metadata_info['alf_file_info_list']
    alf_filename_list = [entry['name'].decode('ascii') for entry in alf_file_info_list]

    archive_entry_info_list = metadata_info['archive_entry_info_list']

    # - the archive file entries order may have already been sorted but for consistency we sort them ourselves
    # - group the archive entries by archive_index
    # so that we can unpack them by the ALF file they belong to
    archive_group_dict = collections.defaultdict(list)
    for entry in archive_entry_info_list:
        archive_group_dict[entry['archive_index']].append(entry)

    # archive_index is mapped to the index of the ALF filename list
    number_of_alf_files = len(alf_filename_list)
    enlighten_counter = enlighten.Counter(total=number_of_alf_files)

    for alf_filename_index in range(number_of_alf_files):
        alf_filename = alf_filename_list[alf_filename_index]
        enlighten_counter.desc = alf_filename
        alf_filepath = os.path.join(metadata_parent, alf_filename)

        try:
            archive_list = archive_group_dict[alf_filename_index]
            handle_single_alf_file(
                filepath=alf_filepath,
                archive_list=archive_list,
            )
        except Exception as ex:
            stack_trace = traceback.format_exc()
            print(f'{shared.FG_RED}ERROR: Error occurs while processing ALF file ({alf_filename}) index {alf_filename_index}{shared.RESET_COLOR}')
            print(stack_trace)
            print(ex)

        enlighten_counter.update()


def main():
    parser = argparse.ArgumentParser(description='Unpack all images from a pickle metadata file log.')
    parser.add_argument('inpath', help='path to the pickle log')
    parser.add_argument('outpath', help='path to the output directory')
    parser.add_argument('--output-format', default='png', choices=IMAGE_OUTPUT_FORMAT_LIST, help='output format')
    parser.add_argument('--force', action='store_true', help='overwrite existing files')

    args = parser.parse_args()
    print('args', args)

    inpath = args.inpath
    with open(inpath, mode='rb') as infile:
        log_list = pickle.load(infile)

    number_of_metadata_logs = len(log_list)
    enlighten_counter = enlighten.Counter(total=number_of_metadata_logs)

    for log_index in range(number_of_metadata_logs):
        try:
            metadata_info = log_list[log_index]
            metadata_filepath = metadata_info['path']
            # enlighten_counter.desc = metadata_filepath
            metadata_parent, metadata_filename = os.path.split(metadata_filepath)
            enlighten_counter.desc = metadata_filename

            # long running function
            handle_metadata_info_obj(log_list[log_index])
        except Exception as ex:
            stack_trace = traceback.format_exc()
            print(f'{shared.FG_RED}ERROR: Error occurs while processing metadata log index {log_index}{shared.RESET_COLOR}')
            print(stack_trace)
            print(ex)

        enlighten_counter.update()


if __name__ == '__main__':
    main()
