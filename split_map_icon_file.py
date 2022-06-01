import os
import io
import time
import traceback
import argparse

import numpy as np
import cv2


def crop_map_icon_image(bgra_image: np.ndarray):
    # split the image horizontally by 8
    # use the first image only
    height, width = bgra_image.shape[:2]
    frame0_0_width = width // 8
    frame0_0 = bgra_image[:, :frame0_0_width]
    frame0_0_height, frame0_0_width = frame0_0.shape[:2]

    # from top to bottom, find the first non-transparent pixel line
    top_index = None
    for y in range(frame0_0_height):
        is_non_transparent = False
        if np.any(frame0_0[y, :] != [0, 0, 0, 0]):
            top_index = y
            break

    if top_index is None:
        raise Exception('failed to find the top index')
    # continue from that line, find the first transparent pixel line
    bottom_index = None
    for y in range(top_index, frame0_0_height):
        if np.all(frame0_0[y, :] == [0, 0, 0, 0]):
            bottom_index = y
            break

    if bottom_index is None:
        raise Exception('failed to find the bottom index')

    frame0_1 = frame0_0[top_index:bottom_index, :]
    frame0_1_height, frame0_1_width = frame0_1.shape[:2]

    left_index = None
    for x in range(frame0_1_width):
        if np.any(frame0_1[:, x] != [0, 0, 0, 0]):
            left_index = x
            break

    if left_index is None:
        raise Exception('failed to find the left index')

    right_index = None
    for x in range(left_index, frame0_1_width):
        if np.all(frame0_1[:, x] == [0, 0, 0, 0]):
            right_index = x
            break

    if right_index is None:
        raise Exception('failed to find the right index')

    map_icon_frame0_region = {
        'left': left_index,
        'top': top_index,
        'right': right_index,
        'bottom': bottom_index,
    }
    cropped_map_icon_frame0 = frame0_1[:, left_index:right_index]

    # map title image
    # continue from the bottom of the map icon image, find the first non-transparent pixel line
    tmp_image0 = bgra_image[bottom_index:, :]
    tmp_image0_height, tmp_image0_width = tmp_image0.shape[:2]

    top_index = None
    for y in range(tmp_image0_height):
        if np.any(tmp_image0[y, :] != [0, 0, 0, 0]):
            top_index = y
            break

    if top_index is None:
        raise Exception('failed to find the top index')

    # continue from that line, find the first transparent pixel line
    for bottom_index in range(top_index, tmp_image0_height):
        if np.all(tmp_image0[bottom_index, :] == [0, 0, 0, 0]):
            break

    for left_index in range(tmp_image0_width):
        if np.any(tmp_image0[:, left_index] != [0, 0, 0, 0]):
            break

    for right_index in range(left_index, tmp_image0_width):
        if np.all(tmp_image0[:, right_index] == [0, 0, 0, 0]):
            break

    map_title_region = {
        'left': left_index,
        'top': top_index,
        'right': right_index,
        'bottom': bottom_index,
    }

    cropped_map_title = tmp_image0[top_index:bottom_index, left_index:right_index]

    return {
        'map_icon_frame0_region': map_icon_frame0_region,
        'cropped_map_icon_frame0': cropped_map_icon_frame0,
        'map_title_region': map_title_region,
        'cropped_map_title': cropped_map_title,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('inputdir', help='input directory')
    parser.add_argument(
        'outputdir',
        default='splitmapiconfileoutputdir',
        nargs='?',
        help='output directory',
    )

    args = parser.parse_args()
    print('args', args)

    inputdir = args.inputdir
    outputdir = args.outputdir

    if not os.path.exists(outputdir):
        os.makedirs(outputdir)

    child_filename_list = os.listdir(inputdir)
    for child_filename in child_filename_list:
        child_filepath = os.path.join(inputdir, child_filename)
        if not os.path.isfile(child_filepath):
            continue

        basename, ext = os.path.splitext(child_filename)
        map_icon_frame0_filename = f'{basename}_map_icon_frame0.png'
        map_title_filename = f'{basename}_map_title.png'

        map_icon_frame0_filepath = os.path.join(outputdir, map_icon_frame0_filename)
        map_title_filepath = os.path.join(outputdir, map_title_filename)

        if os.path.exists(map_icon_frame0_filepath) and os.path.exists(map_title_filepath):
            continue

        print('processing', child_filepath)
        try:
            retval = crop_map_icon_image(cv2.imread(child_filepath, cv2.IMREAD_UNCHANGED))
            if not os.path.exists(map_icon_frame0_filepath):
                cv2.imwrite(
                    map_icon_frame0_filepath,
                    retval['cropped_map_icon_frame0'],
                    [cv2.IMWRITE_PNG_COMPRESSION, 9],
                )

            if not os.path.exists(map_title_filepath):
                cv2.imwrite(
                    map_title_filepath,
                    retval['cropped_map_title'],
                    [cv2.IMWRITE_PNG_COMPRESSION, 9],
                )

        except Exception as ex:
            stacktrace = traceback.format_exc()
            print(ex)
            print(stacktrace)


if __name__ == '__main__':
    main()
