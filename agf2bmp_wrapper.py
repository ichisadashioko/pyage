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


def find_agf_files(inpath: str, log_list: list):
    file_stat = os.stat(inpath)
    if stat.S_ISREG(file_stat.st_mode):
        extension = os.path.splitext(inpath)[1]
        extension = extension.lower()
        if extension == '.agf':
            log_list.append(inpath)
            return
    elif stat.S_ISDIR(file_stat.st_mode):
        child_file_list = os.listdir(inpath)
        for child_file in child_file_list:
            child_fpath = os.path.join(inpath, child_file)
            find_agf_files(child_fpath, log_list)


def create_converting_task_list(
    input_filepath_list: list,
    input_dir: str,
    output_dir: str,
):
    task_list = []

    if output_dir == 'sameasinput':
        for input_filepath in input_filepath_list:
            parent_dir, filename = os.path.split(input_filepath)
            basename, ext = os.path.splitext(filename)
            if ext.lower() == '.bmp':
                raise Exception(f'{input_filepath} has already been converted to PNG!')

            output_filename = basename + '.bmp'

            parent_dir = os.path.dirname(input_filepath)
            output_filepath = os.path.join(parent_dir, output_filename)

            task_list.append({
                'input_filepath': input_filepath,
                'output_filepath': output_filepath,
            })
    else:
        for input_filepath in input_filepath_list:
            rel_path = os.path.relpath(input_filepath, input_dir)
            rel_parent, filename = os.path.split(rel_path)
            base_filename, ext = os.path.splitext(filename)
            if ext.lower() == '.bmp':
                raise Exception(f'{input_filepath} has already been converted to PNG!')

            output_filename = base_filename + '.bmp'
            output_parent_dir = os.path.join(output_dir, rel_parent)
            output_filepath = os.path.join(output_parent_dir, output_filename)

            task_list.append({
                'input_filepath': input_filepath,
                'output_filepath': output_filepath,
            })

    return task_list


class VerboseException(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.args = args
        self.kwargs = kwargs

    def __repr__(self):
        return repr({
            'args': self.args,
            'kwargs': self.kwargs,
        })


class ShellCommandFailedException(VerboseException):
    pass


def datetime_str():
    datetime_obj = datetime.datetime.now()
    datetime_str_without_milliseconds = datetime_obj.strftime('%Y_%m_%d-%H_%M_%S')
    milliseconds_str = repr(datetime_obj.microsecond // 1000).zfill(3)
    return f'{datetime_str_without_milliseconds}.{milliseconds_str}'


def execute_shell_command(
    cmd: str,
    cwd=None,
    timeout=5,
    output_log: list = None,
    log_to_stdout=True,
):
    if output_log is not None:
        output_log.append((time.time(), cmd,))
    if log_to_stdout:
        print(datetime_str(), cmd)

    retval = {
        'input': {
            'command': cmd,
            'cwd': cwd,
            'timeout': timeout,
        },
        'process': None,
        'stdout': None,
        'stderr': None,
        'returncode': None,
        'exception': None,
        'stack_trace': None,
    }

    try:
        ps = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        retval['process'] = ps

        stdout, stderr = ps.communicate(timeout=timeout)
        retval['stdout'] = stdout
        retval['stderr'] = stderr
        retval['returncode'] = ps.returncode
    except Exception as ex:
        stack_trace = traceback.format_exc()
        retval['exception'] = ex
        retval['stack_trace'] = stack_trace

    if output_log is not None:
        output_log.append((time.time(), retval,))
    if log_to_stdout:
        print(datetime_str(), retval)

    return retval


def main():
    parser = argparse.ArgumentParser(description='Convert AGF to PNG')
    parser.add_argument('agf2bmp_exe', type=str, help='Path to agf2bmp.exe')
    parser.add_argument('inpath', help='input file path to search for AGF files')
    parser.add_argument('outpath', nargs='?', default='sameasinput', help='path to the output directory')

    args = parser.parse_args()
    print('args', args)

    inpath = args.inpath
    outpath = args.outpath
    agf2bmp_exe = args.agf2bmp_exe

    if not os.path.exists(inpath):
        raise Exception(f'path {inpath} does not exist')

    agf_filepath_list = []
    find_agf_files(inpath, agf_filepath_list)
    print('len(agf_filepath_list)', len(agf_filepath_list))

    task_list = create_converting_task_list(agf_filepath_list, inpath, outpath)

    error_log = []

    pbar = tqdm.tqdm(task_list)
    for task_info in pbar:
        if os.path.exists('stop'):
            break

        input_filepath = task_info['input_filepath']
        parent_dir, filename = os.path.split(input_filepath)
        pbar.set_description(input_filepath)

        if os.path.exists(task_info['output_filepath']):
            continue

        try:
            execute_shell_command(
                f'{agf2bmp_exe} {input_filepath}',
                cwd=parent_dir,
                timeout=30,
            )
        except Exception as ex:
            stack_trace = traceback.format_exc()
            print(ex)
            print(stack_trace)
            error_log.append({
                'input_filepath': input_filepath,
                'output_filepath': output_filepath,
                'exception': ex,
                'stack_trace': stack_trace,
                'len(agf_content_bs)': len(agf_content_bs),
            })

    print('len(error_log)', len(error_log))
    if len(error_log) > 0:
        error_log_filepath = f'error_log-{time.time_ns()}.pickle'
        print('error_log_filepath', error_log_filepath)

        with open(error_log_filepath, 'wb') as outfile:
            pickle.dump(error_log, outfile)


if __name__ == '__main__':
    main()
