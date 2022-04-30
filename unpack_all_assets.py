# load the pickle log and unpack all the assets
import os
import io
import time
import struct
import pickle
import argparse
import collections

from tqdm import tqdm


def main():
    parser = argparse.ArgumentParser(description='Unpack all assets from a pickle log.')
    parser.add_argument('inpath', help='path to the pickle log')
    parser.add_argument('outpath', help='path to the output directory')

    args = parser.parse_args()
    print('args', args)

    inpath = args.inpath
    with open(inpath, mode='rb') as infile:
        log_list = pickle.load(infile)

    pbar = tqdm(log_list)
    for metadata_info in pbar:
        metadata_filepath = metadata_info['path']
        metadata_parent, metadata_filename = os.path.split(metadata_filepath)
        pbar.set_description(metadata_filename)

        try:
            alf_file_info_list = metadata_info['alf_file_info_list']
            alf_filename_list = [entry['name'].decode('ascii') for entry in alf_file_info_list]

            archive_entry_info_list = metadata_info['archive_entry_info_list']

            # group the archive entries by archive_index
            # so that we can unpack them by the ALF file they belong to
            archive_group_dict = collections.defaultdict(list)
            for entry in archive_entry_info_list:
                archive_group_dict[entry['archive_index']].append(entry)

            # archive_index is mapped to the index of the ALF filename list

        except Exception as ex:
            print(metadata_filepath)
            print(ex)
