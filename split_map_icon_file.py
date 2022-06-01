import os
import io
import time
import traceback
import argparse

import numpy as np
import cv2


def crop_map_title_image(bgra_image: np.ndarray):
    height, width = bgra_image.shape[:2]

    for top_index in range(height):
        is_non_transparent = False
        for x in range(width):
            pixel_value = bgra_image[top_index, x]
            if pixel_value[3] > 0:
                is_non_transparent = True
                break

        if is_non_transparent:
            break

    # continue from that line, find the first transparent pixel line
    for bottom_index in range(top_index, height):
        is_non_transparent = False
        for x in range(width):
            pixel_value = bgra_image[bottom_index, x]
            if pixel_value[3] > 0:
                is_non_transparent = True
                break

        if not is_non_transparent:
            break

    if top_index == bottom_index:
        raise Exception('map title: top_index == bottom_index')

    for left_index in range(width):
        is_non_transparent = False
        for y in range(top_index, bottom_index):
            pixel_value = bgra_image[y, left_index]
            if pixel_value[3] > 0:
                is_non_transparent = True
                break

        if is_non_transparent:
            break

    for right_index in range(left_index, width):
        is_non_transparent = False
        for y in range(top_index, bottom_index):
            pixel_value = bgra_image[y, right_index]
            if pixel_value[3] > 0:
                is_non_transparent = True
                break

        if not is_non_transparent:
            break

    if left_index == right_index:
        raise Exception('map title: left_index == right_index')

    map_title_region = {
        'left': left_index,
        'top': top_index,
        'right': right_index,
        'bottom': bottom_index,
    }

    map_title_image = bgra_image[top_index:bottom_index, left_index:right_index]

    return {
        'region': map_title_region,
        'image': map_title_image,
    }


def crop_map_icon_image(bgra_image: np.ndarray):
    # split the image horizontally by 8
    # use the first image only
    height, width = bgra_image.shape[:2]
    frame0_0_width = width // 8
    frame0_0 = bgra_image[:, :frame0_0_width]
    frame0_0_height, frame0_0_width = frame0_0.shape[:2]

    # from top to bottom, find the first non-transparent pixel line
    for top_index in range(frame0_0_height):
        is_non_transparent = False
        for x in range(frame0_0_width):
            pixel_value = frame0_0[top_index, x]
            if pixel_value[3] > 0:
                is_non_transparent = True
                break

        if is_non_transparent:
            break

    # continue from that line, find the first transparent pixel line
    for bottom_index in range(top_index, frame0_0_height):
        is_non_transparent = False
        for x in range(frame0_0_width):
            pixel_value = frame0_0[bottom_index, x]
            if pixel_value[3] > 0:
                is_non_transparent = True
                break

        if not is_non_transparent:
            break

    if top_index == bottom_index:
        raise Exception('map icon frame0: top_index == bottom_index')

    frame0_1 = frame0_0[top_index:bottom_index, :]
    frame0_1_height, frame0_1_width = frame0_1.shape[:2]

    # from left to right, find the first non-transparent pixel column
    for left_index in range(frame0_1_width):
        is_non_transparent = False
        for y in range(frame0_1_height):
            pixel_value = frame0_1[y, left_index]
            if pixel_value[3] > 0:
                is_non_transparent = True
                break

        if is_non_transparent:
            break

    # continue from that column, find the first transparent pixel column
    for right_index in range(left_index, frame0_1_width):
        is_non_transparent = False
        for y in range(frame0_1_height):
            pixel_value = frame0_1[y, right_index]
            if pixel_value[3] > 0:
                is_non_transparent = True
                break

        if not is_non_transparent:
            break

    if left_index == right_index:
        raise Exception('map icon frame0: left_index == right_index')

    map_icon_frame0_region = {
        'left': left_index,
        'top': top_index,
        'right': right_index,
        'bottom': bottom_index,
    }

    cropped_map_icon_frame0 = frame0_1[:, left_index:right_index]

    # map image can be None
    # map title image

    map_title_image = None
    map_title_image_region = None
    try:
        # continue from the bottom of the map icon image, find the first non-transparent pixel line
        tmp_image0 = bgra_image[bottom_index:, :]
        retval = crop_map_title_image(tmp_image0)
        map_title_image = retval['image']
        map_title_image_region = retval['region']
    except Exception as ex:
        stacktrace = traceback.format_exc()
        print(ex)
        print(stacktrace)

    return {
        'map_icon_frame0_region': map_icon_frame0_region,
        'cropped_map_icon_frame0': cropped_map_icon_frame0,
        'map_title_region': map_title_image_region,
        'map_title_image': map_title_image,
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
                if retval['map_title_image'] is not None:
                    cv2.imwrite(
                        map_title_filepath,
                        retval['map_title_image'],
                        [cv2.IMWRITE_PNG_COMPRESSION, 9],
                    )

        except Exception as ex:
            stacktrace = traceback.format_exc()
            print(ex)
            print(stacktrace)


if __name__ == '__main__':
    main()
