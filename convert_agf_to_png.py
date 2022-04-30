import os
import io
import struct

from tqdm import tqdm

import numpy as np
import cv2

import shared


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

    if agf_type == AGF_TYPE_32BIT:
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


def main():
    pass


if __name__ == '__main__':
    main()
