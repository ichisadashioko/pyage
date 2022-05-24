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

import shared

STOP_FILEPATH = 'stop'


def handle_single_alf_file(
    filepath: str,
    archive_list: list,
    export_config: dict,
    error_log: list,
):
    with open(filepath, mode='rb') as alf_infile:
        number_of_archive_entries = len(archive_list)

        pbar = tqdm.tqdm(range(number_of_archive_entries), leave=True)
        for archive_index in pbar:
            if os.path.exists(STOP_FILEPATH):
                break

            try:
                archive_info = archive_list[archive_index]

                filename_bs = archive_info['name']
                filename = filename_bs.decode('ascii')

                pbar.set_description(filename)

                output_filepath = os.path.join(export_config['destination'], filename)
                if not export_config['force'] and os.path.exists(output_filepath):
                    continue

                if export_config['run']:
                    offset = archive_info['offset']
                    length = archive_info['length']
                    alf_infile.seek(offset)
                    agf_content_bs = alf_infile.read(length)
            except Exception as ex:
                stack_trace = traceback.format_exc()
                print(f'{shared.FG_RED}ERROR: Error occurs while processing archive_info index {archive_index}{shared.RESET_COLOR}')
                print(stack_trace)
                print(ex)
                error_log.append({
                    'exception': ex,
                    'stack_trace': stack_trace,
                    'filepath': filepath,
                    'archive_index': archive_index,
                })


def handle_metadata_info_obj(
    metadata_info: dict,
    export_config: dict,
    error_log: list,
):
    metadata_filepath = metadata_info['path']
    metadata_parent, metadata_filename = os.path.split(metadata_filepath)

    alf_file_info_list = metadata_info['alf_file_info_list']
    alf_filename_list = [entry['name'].decode('ascii') for entry in alf_file_info_list]
    number_of_alf_files = len(alf_filename_list)

    archive_entry_info_list = metadata_info['archive_entry_info_list']

    # - the archive file entries order may have already been sorted but for consistency we sort them ourselves
    # - group the archive entries by archive_index
    # so that we can unpack them by the ALF file they belong to

    if number_of_alf_files > 1:
        archive_group_dict = collections.defaultdict(list)
        for entry in archive_entry_info_list:
            archive_group_dict[entry['archive_index']].append(entry)

    # archive_index is mapped to the index of the ALF filename list

    if number_of_alf_files == 0:
        print(f'{shared.FG_RED}ERROR: No ALF files found in {metadata_filepath}{shared.RESET_COLOR}')
        return
    elif number_of_alf_files == 1:
        alf_filename = alf_filename_list[0]
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
                        return

            child_export_config = {
                'destination': export_dir,
                'force': export_config['force'],
                'run': export_config['run'],
            }

            archive_list = archive_entry_info_list
            handle_single_alf_file(
                filepath=alf_filepath,
                archive_list=archive_list,
                export_config=child_export_config,
                error_log=error_log,
            )
        except Exception as ex:
            stack_trace = traceback.format_exc()
            print(f'{shared.FG_RED}ERROR: Error occurs while processing ALF file ({alf_filename}){shared.RESET_COLOR}')
            print(stack_trace)
            print(ex)
            error_log.append({
                'exception': ex,
                'stack_trace': stack_trace,
                'metadata_filepath': metadata_filepath,
                'alf_filename_index': 0,
                'alf_filename': alf_filename,
                'export_config': export_config,
            })
    else:
        pbar = tqdm.tqdm(range(number_of_alf_files), leave=True)
        for alf_filename_index in pbar:
            if os.path.exists(STOP_FILEPATH):
                break

            alf_filename = alf_filename_list[alf_filename_index]
            pbar.set_description(alf_filename)
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
                    'force': export_config['force'],
                    'run': export_config['run'],
                }

                archive_list = archive_group_dict[alf_filename_index]
                handle_single_alf_file(
                    filepath=alf_filepath,
                    archive_list=archive_list,
                    export_config=child_export_config,
                    error_log=error_log,
                )
            except Exception as ex:
                stack_trace = traceback.format_exc()
                print(f'{shared.FG_RED}ERROR: Error occurs while processing ALF file ({alf_filename}) index {alf_filename_index}{shared.RESET_COLOR}')
                print(stack_trace)
                print(ex)
                error_log.append({
                    'exception': ex,
                    'stack_trace': stack_trace,
                    'metadata_filepath': metadata_filepath,
                    'alf_filename_index': alf_filename_index,
                    'alf_filename': alf_filename,
                    'export_config': export_config,
                })


def main():
    parser = argparse.ArgumentParser(description='Unpack all assets from a pickle metadata file log.')
    parser.add_argument('inpath', help='path to the pickle log')
    parser.add_argument('outpath', nargs='?', default='sameasinput', help='path to the output directory')
    parser.add_argument('--force', action='store_true', help='overwrite existing files')
    parser.add_argument('-r', '--run', action='store_true', help='actually destroying your files')

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
        'force': args.force,
        'destination': outpath,
        'run': args.run,
    }

    error_log = []

    with open(pickle_filepath, mode='rb') as infile:
        log_list = pickle.load(infile)

    number_of_metadata_logs = len(log_list)

    if number_of_metadata_logs == 0:
        print(f'{shared.FG_RED}ERROR: No metadata log found in {pickle_filepath}{shared.RESET_COLOR}')
        return
    elif number_of_metadata_logs == 1:
        try:
            metadata_info = log_list[0]
            metadata_filepath = metadata_info['path']
            # enlighten_counter.desc = metadata_filepath
            metadata_parent, metadata_filename = os.path.split(metadata_filepath)

            # long running function
            handle_metadata_info_obj(
                metadata_info,
                export_config=EXPORT_CONFIG,
                error_log=error_log,
            )
        except Exception as ex:
            stack_trace = traceback.format_exc()
            print(f'{shared.FG_RED}ERROR: Error occurs while processing metadata log{shared.RESET_COLOR}')
            print(stack_trace)
            print(ex)
            error_log.append({
                'exception': ex,
                'stack_trace': stack_trace,
                'log_index': 0,
                'pickle_filepath': pickle_filepath,
                'export_config': EXPORT_CONFIG,
            })
    else:
        pbar = tqdm.tqdm(range(number_of_metadata_logs))
        for log_index in pbar:
            if os.path.exists(STOP_FILEPATH):
                break

            try:
                metadata_info = log_list[log_index]
                metadata_filepath = metadata_info['path']
                # enlighten_counter.desc = metadata_filepath
                metadata_parent, metadata_filename = os.path.split(metadata_filepath)
                pbar.set_description(metadata_filename)

                # long running function
                handle_metadata_info_obj(
                    metadata_info,
                    export_config=EXPORT_CONFIG,
                    error_log=error_log,
                )
            except Exception as ex:
                stack_trace = traceback.format_exc()
                print(f'{shared.FG_RED}ERROR: Error occurs while processing metadata log index {log_index}{shared.RESET_COLOR}')
                print(stack_trace)
                print(ex)
                error_log.append({
                    'exception': ex,
                    'stack_trace': stack_trace,
                    'log_index': log_index,
                    'pickle_filepath': pickle_filepath,
                    'export_config': EXPORT_CONFIG,
                })


if __name__ == '__main__':
    main()
