import os
import io
import struct
import argparse
import stat
import traceback
import pickle
import time
import threading
import subprocess
import datetime

from tqdm import tqdm

import numpy as np
import cv2

import tqdm

import shared

IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.bmp']

def find_image_files(inpath: str, log_list: list):
    file_stat = os.stat(inpath)
    if stat.S_ISREG(file_stat.st_mode):
        extension = os.path.splitext(inpath)[1]
        extension = extension.lower()
        if extension in IMAGE_EXTENSIONS:
            log_list.append(inpath)
            return
    elif stat.S_ISDIR(file_stat.st_mode):
        child_file_list = os.listdir(inpath)
        for child_file in child_file_list:
            child_fpath = os.path.join(inpath, child_file)
            find_image_files(child_fpath, log_list)


def main():
    parser = argparse.ArgumentParser(description='Convert AGF to PNG')
    parser.add_argument('inpath', help='input file path to search for AGF files')
    parser.add_argument('outpath', help='path to the output directory')
    parser.add_argument('--force', action='store_true', help='overwrite existing files')
    parser.add_argument('-r', '--run', action='store_true', help='actually destroying your files')
    parser.add_argument('--clean', action='store_true', help='remove PNG files')

    args = parser.parse_args()
    print('args', args)

    inpath = args.inpath
    outpath = args.outpath
    force = args.force
    run = args.run
    clean = args.clean

    if not os.path.exists(inpath):
        raise Exception(f'path {inpath} does not exist')

    image_filepath_list = []
    find_image_files(inpath, image_filepath_list)
    print('len(image_filepath_list)', len(image_filepath_list))

    input_dir = inpath
    output_dir = outpath

    pbar = tqdm.tqdm(image_filepath_list)
    for input_filepath in pbar:
        if os.path.exists('stop'):
            break

        rel_path = os.path.relpath(input_filepath, input_dir)
        rel_parent, filename = os.path.split(rel_path)
        output_parent_dir = os.path.join(output_dir, rel_parent)
        output_filepath = os.path.join(output_parent_dir, filename)
        pbar.set_description(input_filepath)

        if not os.path.exists(output_parent_dir):
            os.makedirs(output_parent_dir)

        os.rename(input_filepath, output_filepath)

if __name__ == '__main__':
    main()
