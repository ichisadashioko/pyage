import os
import io
import struct
import argparse
import stat
import traceback
import pickle
import time

from tqdm import tqdm

import numpy as np
import cv2

import tqdm

import shared


def convert_rgb_to_opencv_format(
    rgb_image: np.ndarray,
):
    image_shape = rgb_image.shape
    if len(image_shape) == 2:
        # grayscale image
        return rgb_image
    elif len(image_shape) == 3:
        if image_shape[2] == 2:
            # grayscale with alpha
            grayscale_image = rgb_image[:, :, 0]
            alpha_image = rgb_image[:, :, 1]
            bgra_image = np.zeros((image_shape[0], image_shape[1], 4), dtype=np.uint8)
            bgra_image[:, :, 0] = grayscale_image
            bgra_image[:, :, 1] = grayscale_image
            bgra_image[:, :, 2] = grayscale_image
            bgra_image[:, :, 3] = alpha_image
            return bgra_image
        elif image_shape[2] == 3:
            # RGB image
            return cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)
        elif image_shape[2] == 4:
            # RGBA image
            return cv2.cvtColor(rgb_image, cv2.COLOR_RGBA2BGRA)
        else:
            raise Exception(f'Unsupported image shape {image_shape}')


def convert_agf_data_to_numpy_array(
    agf_content_bs: bytes,
    force_rgb=False
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
    if agf_type not in [shared.AGF_TYPE_24BIT, shared.AGF_TYPE_32BIT]:
        raise Exception(f'AGF unknown type {agf_type}')

    bitmap_header_bs = shared.read_lzss_section(stream)
    bitmap_header = shared.parse_agf_bitmap_header_bs(bitmap_header_bs)
    image_data_bs = shared.read_lzss_section(stream)

    bitmap_info_header = bitmap_header['BITMAPINFOHEADER']
    biWidth = bitmap_info_header['biWidth']
    biHeight = bitmap_info_header['biHeight']
    biBitCount = bitmap_info_header['biBitCount']

    if biHeight < 0:
        raise Exception(f'Unsupported bitmap order TODO biHeight < 0')

    if biBitCount % 8 != 0:
        raise Exception(f'biBitCount={biBitCount} is not multiple of 8')

    bytes_per_pixel = biBitCount // 8
    biClrUsed = bitmap_info_header['biClrUsed']

    biCompression = bitmap_info_header['biCompression']
    if biCompression != 0:
        raise Exception(f'unsupported biCompression value {biCompression}')

    if agf_type == shared.AGF_TYPE_32BIT:
        # ACIF header format
        # 4 bytes: signature
        # 4 bytes: type
        # 4 bytes: unknown
        # 4 bytes: original_length
        # 4 bytes: width
        # 4 bytes: height
        acif_header_bs = stream.read(24)
        if len(acif_header_bs) != 24:
            raise Exception(f'ACIF header is not 24 bytes long - {len(acif_header_bs)}')
        {
            'signature': acif_header_bs[0:4],
            'type': acif_header_bs[4:8],
            'unknown': acif_header_bs[8:12],
            'original_length': acif_header_bs[12:16],
            'width': acif_header_bs[16:20],
            'height': acif_header_bs[20:24],
        }

        transparency_data_bs = shared.read_lzss_section(stream)

        ################################################################
        # I am not sure if the image_data_bs contains only the indexes of the palette
        # or if it contains the actual image data
        # if it contains the actual image data, then the image_data_bs_len should be
        # biWidth * biHeight * bytes_per_pixel
        # The biClrUsed value should be used to determine that the image_data_bs contains
        # the actual image data or not. However I am not sure if the biClrUsed value
        # is always correct.
        # if biClrUsed == 0, I think it means that the image_data_bs contains the actual image data
        # However, I found an example where biClrUsed == 0 but the image_data_bs_len is not
        # biWidth * biHeight * bytes_per_pixel

        image_data_bs_len = len(image_data_bs)
        if image_data_bs_len == int(biWidth * biHeight * bytes_per_pixel):
            tmp_np_array = np.frombuffer(image_data_bs, dtype=np.uint8)
            bgr_image = tmp_np_array.reshape((biHeight, biWidth, bytes_per_pixel))
            reorder_bgr_image = np.flipud(bgr_image)

            # merge the transparency array with the image data
            tmp_np_array = np.frombuffer(transparency_data_bs, dtype=np.uint8)
            transparency_array = tmp_np_array.reshape((biHeight, biWidth, 1))
            bgra_image = np.concatenate((reorder_bgr_image, transparency_array), axis=2)
            return bgra_image

        ################################################################
        else:
            # generate dictionary of RGBQUAD - which is a palette containing the colors
            # the image_data_bs is now a list of indexes into the palette
            rgb_quad_array_bs = bitmap_header['RGBQUAD']
            tmp_np_array = np.frombuffer(rgb_quad_array_bs, dtype=np.uint8)
            rgb_quad_array = tmp_np_array.reshape((-1, 4))

            tmp_np_array = np.frombuffer(image_data_bs, dtype=np.uint8)
            image_index_array = tmp_np_array.reshape(biHeight, biWidth)
            # map the indexes into the palette to the RGBQUAD
            image_data_array = np.array([rgb_quad_array[i] for i in image_index_array])
    else:
        # TODO this is the place where we want to transform the image data into what we want either as a BMP image with minimal processing with Windows API or as PNG/JPEG image

        # bgr_image = np.zeros(
        #     (biHeight, biWidth, bytes_per_pixel),
        #     dtype=np.uint8,
        # )

        # for y in tqdm(range(biHeight)):
        #     for x in range(biWidth):
        #         current_pixel_index = ((y * biWidth) + x) * bytes_per_pixel
        #         for z in range(bytes_per_pixel):
        #             value = image_data_bs[current_pixel_index + z]
        #             bgr_image[y,x,z] = value

        tmp_np_array = np.frombuffer(image_data_bs, dtype=np.uint8)

        if bytes_per_pixel == 1:
            gray_image = tmp_np_array.reshape(biHeight, biWidth)
            return gray_image

        bgr_image = tmp_np_array.reshape((biHeight, biWidth, bytes_per_pixel))
        if force_rgb:
            rgb_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
            return rgb_image
        else:
            return bgr_image


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
            if ext.lower() == '.png':
                raise Exception(f'{input_filepath} has already been converted to PNG!')

            output_filename = basename + '.png'

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
            if ext.lower() == '.png':
                raise Exception(f'{input_filepath} has already been converted to PNG!')

            output_filename = base_filename + '.png'
            output_parent_dir = os.path.join(output_dir, rel_parent)
            output_filepath = os.path.join(output_parent_dir, output_filename)

            task_list.append({
                'input_filepath': input_filepath,
                'output_filepath': output_filepath,
            })

    return task_list


def main():
    parser = argparse.ArgumentParser(description='Convert AGF to PNG')
    parser.add_argument('inpath', help='input file path to search for AGF files')
    parser.add_argument('outpath', nargs='?', default='sameasinput', help='path to the output directory')
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
        output_filepath = task_info['output_filepath']
        pbar.set_description(input_filepath)

        if run and clean:
            if os.path.exists(output_filepath):
                os.remove(output_filepath)
            continue

        if not force and os.path.exists(output_filepath):
            continue

        if not run:
            continue

        agf_content_bs = open(input_filepath, 'rb').read()

        try:
            # TODO handle BMP format with minimal processing to reduce execution time
            rgb_image = convert_agf_data_to_numpy_array(
                agf_content_bs=agf_content_bs,
                force_rgb=True,
            )

            cv2_image = convert_rgb_to_opencv_format(rgb_image)
            parent_dir, filename = os.path.split(output_filepath)
            if not os.path.exists(parent_dir):
                os.makedirs(parent_dir)
            cv2.imwrite(output_filepath, cv2_image, [cv2.IMWRITE_PNG_COMPRESSION, 9])
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
