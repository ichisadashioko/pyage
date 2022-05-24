# load the pickle log and unpack all the assets
import os
import io
import time
import struct
import pickle
import argparse
import collections
import traceback

import tqdm
import enlighten

import numpy as np
import cv2

import shared

import convert_agf_to_png


IMAGE_OUTPUT_FORMAT_LIST = ['png', 'bmp', 'jpg']


def convert_rgb_to_opencv_format(
    rgb_image: np.ndarray,
):
    image_shape = rgb_image.shape
    if len(image_shape) == 2:
        # grayscale image
        return rgb_image
    elif len(image_shape) == 3:
        if image_shape[2] == 3:
            # RGB image
            return cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)
        elif image_shape[2] == 4:
            # RGBA image
            return cv2.cvtColor(rgb_image, cv2.COLOR_RGBA2BGRA)
        else:
            raise Exception(f'Unsupported image shape {image_shape}')


def handle_single_alf_file(
    filepath: str,
    archive_list: list,
    export_config: dict,
):
    with open(filepath, mode='rb') as alf_infile:
        number_of_archive_entries = len(archive_list)
        enlighten_counter = enlighten.Counter(total=number_of_archive_entries)

        for archive_index in range(number_of_archive_entries):
            try:
                archive_info = archive_list[archive_index]

                filename_bs = archive_info['name']
                filename = filename_bs.decode('ascii')
                base_filename, ext = os.path.splitext(filename)

                ext = ext.lower()
                if not ext == '.agf':
                    enlighten_counter.update()
                    continue

                output_filename = base_filename + '.' + export_config['format']
                output_filepath = os.path.join(export_config['destination'], output_filename)
                if not export_config['force'] and os.path.exists(output_filepath):
                    enlighten_counter.update()
                    continue

                offset = archive_info['offset']
                length = archive_info['length']
                alf_infile.seek(offset)
                agf_content_bs = alf_infile.read(length)

                # TODO handle BMP format with minimal processing to reduce execution time
                rgb_image = convert_agf_to_png.convert_agf_data_to_numpy_array(
                    agf_content_bs=agf_content_bs,
                    force_rgb=True,
                )

                cv2_image = convert_rgb_to_opencv_format(rgb_image)

                if export_config['format'] == 'png':
                    cv2.imwrite(output_filepath, cv2_image, [cv2.IMWRITE_PNG_COMPRESSION, 9])
                else:
                    cv2.imwrite(output_filepath, cv2_image)
            except Exception as ex:
                stack_trace = traceback.format_exc()
                print(f'{shared.FG_RED}ERROR: Error occurs while processing archive_info index {archive_index}{shared.RESET_COLOR}')
                print(stack_trace)
                print(ex)

            enlighten_counter.update()


def handle_metadata_info_obj(
    metadata_info: dict,
    export_config: dict,
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
            if export_config['destination'] == 'sameasinput':
                alf_basename = os.path.splitext(alf_filename)[0]
                export_dir = os.path.join(metadata_parent, alf_basename)
            else:
                export_dir = os.path.join(export_config['destination'], alf_filename)
                if not os.path.exists(export_dir):
                    try:
                        os.makedirs(export_dir)
                    except Exception as ex:
                        print(f'{shared.FG_RED}ERROR: Failed to create directory {export_dir}{shared.RESET_COLOR}')
                        print(ex)
                        continue

            child_export_config = {
                'destination': export_dir,
                'format': export_config['format'],
                'force': export_config['force'],
            }

            archive_list = archive_group_dict[alf_filename_index]
            handle_single_alf_file(
                filepath=alf_filepath,
                archive_list=archive_list,
                export_config=child_export_config,
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
    parser.add_argument('outpath', nargs='?', default='sameasinput', help='path to the output directory')
    parser.add_argument('--output-format', default='png', choices=IMAGE_OUTPUT_FORMAT_LIST, help='output format')
    parser.add_argument('--force', action='store_true', help='overwrite existing files')

    args = parser.parse_args()
    print('args', args)

    pickle_filepath = args.inpath
    outpath = args.outpath

    if not os.path.exists(pickle_filepath):
        print(f'{shared.FG_RED}ERROR: Pickle file does not exist: {pickle_filepath}{shared.RESET_COLOR}')
        return

    if outpath != 'sameasinput':
        outpath = os.path.abspath(outpath)
        if not os.path.exists(outpath):
            try:
                os.makedirs(outpath)
            except Exception as ex:
                print(f'{shared.FG_RED}ERROR: Failed to create output directory: {outpath}{shared.RESET_COLOR}')
                print(stack_trace)
                print(ex)
                return

    EXPORT_CONFIG = {
        'format': args.output_format,
        'force': args.force,
        'destination': outpath,
    }

    with open(pickle_filepath, mode='rb') as infile:
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
            handle_metadata_info_obj(
                log_list[log_index],
                export_config=EXPORT_CONFIG,
            )
        except Exception as ex:
            stack_trace = traceback.format_exc()
            print(f'{shared.FG_RED}ERROR: Error occurs while processing metadata log index {log_index}{shared.RESET_COLOR}')
            print(stack_trace)
            print(ex)

        enlighten_counter.update()


if __name__ == '__main__':
    main()
