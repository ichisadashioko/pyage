import os
import io
import argparse
import struct
import traceback
import pickle

from tqdm import tqdm


def find_all_bin_files(
    inpath: str,
    output_log: list,
):
    if(os.path.isfile(inpath)):
        ext = os.path.splitext(inpath)[1]
        ext = ext.lower()
        if ext == '.bin':
            output_log.append(inpath)
    elif os.path.isdir(inpath):
        child_filename_list = os.listdir(inpath)
        for child_filename in child_filename_list:
            child_filepath = os.path.join(inpath, child_filename)
            find_all_bin_files(
                inpath=child_filepath,
                output_log=output_log,
            )


# instruction definition format (type, name, number of arguments)
INSTRUCTION_DEFINITION_LIST = [
    (0x1, "u004149C0", 0x0),  # error
    (0x2, "exit", 0x0),
    (0x3, "call-script", 0x1),  # call another script, param = SYSTEM4.bin index
    (0x4, "u00417E30", 0x2),
    (0x5, "ret", 0x0),
    (0x6, "u00417E80", 0x2),
    (0x7, "u00417F90", 0x1),
    (0x8, "u00417FC0", 0x1),
    (0x9, "exit-script", 0x0),
    (0xA, "u00424170", 0x2),
    (0xB, "u00418090", 0xB),
    (0xC, "u004149E0", 0x0),
    (0xD, "u004181A0", 0x4),
    (0xE, "u00418200", 0xC),
    (0xF, "u00418300", 0x1),
    (0x10, "u00414A00", 0x4),
    (0x11, "u00418330", 0x9),
    (0x12, "u004183F0", 0x1),
    (0x13, "u00418420", 0x4),
    (0x14, "u00414A20", 0x0),
    (0x15, "u00418490", 0x5),
    (0x16, "u00418520", 0x2),
    (0x17, "u00418560", 0x2),
    (0x1E, "u004185B0", 0x8),
    (0x1F, "u00418690", 0xC),
    (0x20, "u004187C0", 0x6),
    (0x21, "u00418860", 0x2),
    (0x22, "u00418920", 0x2),
    (0x23, "u004189D0", 0x2),
    (0x24, "u00418A90", 0x2),
    (0x25, "u00418B40", 0x3),
    (0x26, "u00418C00", 0x4),
    (0x27, "u00418CC0", 0x4),
    (0x28, "u00418D90", 0x4),
    (0x2A, "u00418E60", 0x4),
    (0x2B, "u00418F30", 0x5),
    (0x2C, "u00419010", 0x5),
    (0x2D, "u004190A0", 0xC),
    (0x2E, "u004194B0", 0x5),
    (0x2F, "u004195A0", 0x4),
    (0x30, "u00419670", 0x5),
    (0x31, "u00419750", 0x4),
    (0x32, "u004197C0", 0xA),
    (0x33, "u00419900", 0x6),
    (0x34, "u004199C0", 0xC),
    (0x35, "u00419AF0", 0xB),
    (0x36, "u00419C00", 0x3),
    (0x37, "u00419C90", 0xB),
    (0x38, "u00419DA0", 0xC),
    (0x50, "add", 0x3),  # add. param1 = param2 + param3
    (0x51, "sub", 0x3),  # sub. param1 = param2 - param3
    (0x52, "mul", 0x3),  # mul. param1 = param2 * param3
    (0x53, "div", 0x3),  # div. param1 = param2 / param3
    (0x54, "mod", 0x3),  # mod. param1 = param2 % param3
    (0x55, "mov", 0x2),  # mov. param1 = param2
    (0x56, "and", 0x3),  # and. param1 = param2 & param3
    (0x57, "or", 0x3),  # or. param1 = param2 | param3
    (0x58, "sar", 0x3),  # sar. param1 = param2 >> param3
    (0x59, "shl", 0x3),  # shl. param1 = param2 << param3
    (0x5A, "eq", 0x3),  # eq. param1 = param2 == param3
    (0x5B, "ne", 0x3),  # ne. param1 = param2 != param3
    (0x5C, "lt", 0x3),  # lt. param1 = param2 < param3
    (0x5D, "lte", 0x3),  # lte. param1 = param2 <= param3
    (0x5E, "gr", 0x3),  # gr. param1 = param2 > param3
    (0x5F, "gre", 0x3),  # gre. param1 = param2 >= param3
    (0x60, "u0041A270", 0x2),
    (0x61, "lookup-array", 0x3),  # lookup. param1 = param2[param3]
    (0x62, "u0041A360", 0x3),
    (0x63, "u00414A60", 0x2),
    (0x64, "copy-local-array", 0x2),
    (0x65, "u00414AA0", 0x2),
    (0x66, "u00414AE0", 0x3),
    (0x67, "u00414B20", 0x3),
    (0x68, "u00414B60", 0x3),
    (0x69, "u00414BA0", 0x3),
    (0x6A, "u00414BE0", 0x3),
    (0x6B, "u00414C20", 0x3),
    (0x6C, "copy-to-global", 0x2),  # loop copy local value to global array, param1 = array start, param2 = count
    (0x6D, "u00416960", 0x0),
    (0x6E, "show-text", 0x2),
    (0x6F, "end-text-line", 0x1),
    (0x70, "u0041A750", 0x5),
    (0x71, "u0041A7B0", 0x1),
    (0x72, "wait-for-input", 0x1),
    (0x73, "u0041AB30", 0xA),
    (0x74, "u0041AC00", 0x1),
    (0x75, "u0041AC30", 0x1),
    (0x76, "u0041AC60", 0x1),
    (0x77, "u0041ACB0", 0x1),
    (0x78, "u0041AD00", 0x1),
    (0x79, "u0041AD30", 0x3),
    (0x7A, "u0041AD70", 0x3),
    (0x7B, "u0041ADB0", 0x2),  # ukn, both args point to code locations
    (0x7C, "u00416A90", 0x0),
    (0x7D, "u0041AE00", 0x2),
    (0x7E, "u0041AEA0", 0x1),
    (0x7F, "u00414C60", 0x1),
    (0x80, "u0041AF00", 0x1),
    (0x81, "u0041AF30", 0x1),
    (0x82, "u0041AF80", 0x5),
    (0x83, "u00414C90", 0x3),
    (0x84, "u0041AFE0", 0x1),
    (0x85, "u00414CF0", 0x0),
    (0x86, "u0041B210", 0x1),
    (0x87, "u00414D10", 0x0),
    (0x88, "u0041B290", 0x1),
    (0x89, "u0041B2E0", 0x4),
    (0x8A, "u0041B330", 0x6),
    (0x8B, "u0041B3D0", 0x1),
    (0x8C, "jmp", 0x1),
    (0x8D, "u0041BCE0", 0x2),
    (0x8E, "u0041BD60", 0x1),
    (0x8F, "call", 0x1),
    (0x90, "u0041BEB0", 0x7),  # ukn, args 5, 6 and 7 point to code locations
    (0x91, "u0041BFB0", 0x1),
    (0x92, "u0041C030", 0x2),
    (0x93, "u00415040", 0x0),
    (0x94, "u00415090", 0x0),
    (0x95, "u0041C0C0", 0x2),
    (0x96, "u004150C0", 0x0),
    (0x97, "u0041C150", 0x5),
    (0xA0, "jcc", 0x3),
    (0xA1, "u00427C00", 0x0),
    (0xA2, "u00427FD0", 0x2),
    (0xA3, "u004244D0", 0x2),
    (0xAA, "u0041C270", 0x2),
    (0xAB, "u0041C330", 0x2),
    (0xAC, "u0041C3E0", 0x9),
    (0xAD, "u00415110", 0x0),
    (0xAE, "u00415130", 0x0),
    (0xAF, "u00415480", 0x0),
    (0xB0, "u0041C530", 0x1),
    (0xB1, "u0041C560", 0x1),
    (0xB2, "u0041C590", 0x2),
    (0xB3, "u004154B0", 0x0),
    (0xB4, "play-sound-effect", 0x2),    # play a sound effect/ambient. param1 = file index, param2 = play mode?
    (0xB5, "u0041D050", 0x1),
    (0xB6, "u0041D080", 0x1),
    (0xB7, "u0041D0E0", 0x1),
    (0xB8, "u00415520", 0x0),
    (0xB9, "u0041D140", 0x1),
    (0xBA, "u0041D0B0", 0x1),
    (0xBB, "u0041D250", 0x1),
    (0xBC, "u0041D280", 0x1),
    (0xBD, "u00415570", 0x1),
    (0xBE, "u004155E0", 0x1),
    (0xBF, "play-bgm", 0x1),  # param1 = bgm number
    (0xC0, "u00415620", 0x1),
    (0xC1, "u00415650", 0x0),
    (0xC2, "u0041D2B0", 0x2),
    (0xC3, "u0041D390", 0x1),
    (0xC4, "play-voice", 0x1),
    (0xC5, "u0041D4A0", 0x2),
    (0xC6, "u0041D5D0", 0x2),
    (0xC7, "u0041D760", 0x2),
    (0xC8, "sleep", 0x1),        # param1 = sleep time?
    (0xC9, "u00415770", 0x0),
    (0xCA, "u004157A0", 0x0),
    (0xCB, "u00415800", 0x1),
    (0xCC, "mouse_callback", 0x2),  # sets mouse/keyboard callback location, param1 = id, param2 = offset (minus header, not multiplied by 4)
    (0xCD, "get-input-type", 0x0),  # get input type, mouse, keyboard, pad etc
    (0xCE, "u0041E0B0", 0x3),
    (0xCF, "u00416D40", 0x0),
    (0xD0, "u00415830", 0x1),
    (0xD1, "u00415860", 0x0),
    (0xD2, "u0041E110", 0x1),
    (0xD3, "u00425960", 0x0),
    (0xD4, "u004266F0", 0x4),  # seems to setup some kind of looping function calls. param1 = ukn, param2 = loop count, param3 = function location?, param4 = function location?
    (0xD5, "u004262C0", 0x1),
    (0xD6, "u004267D0", 0x6),
    (0xD7, "u0041E1A0", 0x1),
    (0xD8, "u0041E150", 0x2),
    (0xD9, "u00415880", 0x0),
    (0xDA, "u004158B0", 0x6),
    (0xFA, "u00415940", 0x0),
    (0xFB, "joy_callback", 0x2),  # sets code callback for joystick inputs. ID 0-4= left thumb up/down/left/right, 4 = X on Xbox controller etc. param1 = id, param2 = offset (minus header, not multiplied by 4)
    (0xFC, "u004159F0", 0x0),
    (0xFD, "u0041E2D0", 0x2),
    (0xFE, "u0041E360", 0x1),
    (0xFF, "u00415A10", 0x0),
    (0x100, "u00415A60", 0x0),
    (0x101, "u00415BF0", 0x0),  # joystick input?
    (0x102, "u0041E3C0", 0x3),
    (0x103, "u0041E4A0", 0x1),
    (0x104, "u00415C50", 0x0),
    (0x105, "u0041E4D0", 0x1),
    (0x106, "u00415E40", 0x1),
    (0x107, "u0041E500", 0x2),
    (0x108, "u00415E70", 0x1),
    (0x109, "u00415EC0", 0x2),
    (0x10A, "u0041E540", 0x2),
    (0x10B, "u0041E5A0", 0x2),
    (0x10C, "u0041E5E0", 0x2),
    (0x10D, "u00415F10", 0x1),
    (0x10E, "u0041E650", 0x2),
    (0x10F, "u0041E690", 0x1),
    (0x12C, "lookup-array-2d", 0x5),  # 2d array lookup. param1 = param2[(param3 * param4) + param5]
    (0x12D, "u0041E720", 0x7),
    (0x12E, "u0041E940", 0x8),
    (0x12F, "u0041ECB0", 0x4),
    (0x130, "u00415F40", 0x1),
    (0x131, "u00415F70", 0x1),
    (0x132, "u0041EF00", 0x1),
    (0x133, "u0041EFF0", 0x2),
    (0x134, "u0041F050", 0x3),
    (0x135, "bit-set", 0x2),    # bts, param1 = param1  OR param2
    (0x136, "bit-reset", 0x2),    # btr, param1 = param1 NOR param2
    (0x137, "u0041F1C0", 0x1),
    (0x138, "u0041F2B0", 0x2),
    (0x139, "u0041F310", 0x3),
    (0x13A, "u0041F3A0", 0x6),
    (0x13B, "u0041F440", 0x7),
    (0x13C, "u0041F7E0", 0x1),
    (0x13D, "u0041F840", 0x3),
    (0x13E, "u0041F8D0", 0x2),
    (0x13F, "check-bit", 0x3),  # param1 = param2 & (1 << param3). Neg, sbb, neg to get the result as a bool
    (0x140, "u0041F9C0", 0x4),
    (0x141, "u0041FAA0", 0x1),
    (0x142, "u0041FB10", 0x1),
    (0x143, "u00415FB0", 0x0),
    (0x144, "u004259D0", 0x2),
    (0x145, "u00416040", 0x1),
    (0x146, "u0041FB40", 0x1),
    (0x147, "u0041FB80", 0x6),
    (0x148, "u004160A0", 0x1),
    (0x149, "u0041FCE0", 0x1),
    (0x14A, "u0041FD10", 0x7),
    (0x14B, "u0041FF50", 0x1),
    (0x14C, "set-agerc-export", 0x2),  # binds an agerc.dll export name to the given number
    (0x14D, "call-agerc-export", 0x6),  # call the param1 agerc exported function
    (0x190, "u0041C5E0", 0x2),
    (0x191, "u0041A4A0", 0x2),
    (0x192, "set-string", 0x2),  # u004252D0 : set-string. param1 = param2
    (0x193, "concat", 0x3),  # u00425370 : concat. param1 = param2.concat(param3)
    (0x194, "u00425480", 0x3),
    (0x195, "u00425580", 0x3),
    (0x196, "display-furigana", 0x3),  # u0041B400 : display-furigana. param1 = text, param2 = furigana
    (0x197, "u0041B510", 0x1),
    (0x198, "u0041B540", 0x3),
    (0x199, "u00414D50", 0x0),
    (0x19A, "u00414E50", 0x1),
    (0x19B, "u00414E80", 0x0),
    (0x19C, "u00414EC0", 0x0),
    (0x19D, "u0041C680", 0x2),
    (0x19E, "u0041C6E0", 0x2),
    (0x19F, "u0041C860", 0x2),
    (0x1A0, "u0041C9B0", 0x9),
    (0x1A1, "u0041CB40", 0x2),
    (0x1A2, "u00428010", 0x1),
    (0x1A3, "string-lookup-set", 0x1),  # check the value given exists in save/current data and set. param1 = strings[param1]
    (0x1A4, "u0041B580", 0x2),
    (0x1A5, "set-font", 0x1),  # set-font
    (0x1A6, "halve-strlen", 0x2),  # halve-strlen? param1 = param2.length() / 2 (rounded down)
    (0x1A7, "comment", 0x1),    # Developer debug comment
    (0x1A8, "dev_ukn", 0x0),    # Developer debug something, no function in-game
    (0x1A9, "u00428090", 0x1),
    (0x1AA, "u00425920", 0x1),
    (0x1AB, "u0041CCA0", 0x2),
    (0x1AC, "u0041CD80", 0x3),
    (0x1AD, "u004154F0", 0x0),
    (0x1AE, "u0041CED0", 0x3),
    (0x1AF, "u004245C0", 0x3),
    (0x1B0, "u0041A510", 0x3),
    (0x1B1, "u0041B5C0", 0x1),
    (0x1B2, "u00425790", 0x1),  # to string table?
    (0x1B3, "u004257D0", 0x0),
    (0x1B4, "u004237C0", 0x0),
    (0x1B5, "u0041B5F0", 0x1),
    (0x1B6, "u00414F60", 0x1),
    (0x1B7, "u0041B640", 0x1),
    (0x1B8, "u0041B670", 0x2),
    (0x1B9, "u0041B710", 0x2),
    (0x1BA, "u0041D850", 0x2),
    (0x1BB, "u0041B7B0", 0x1),
    (0x1BC, "u00415670", 0x0),
    (0x1BD, "u0041D910", 0x1),
    (0x1BE, "u0041D9D0", 0x2),
    (0x1BF, "u004156C0", 0x0),
    (0x1C0, "u0041DB70", 0x1),
    (0x1C1, "u0041B820", 0x3),
    (0x1C2, "u0041B860", 0x2),
    (0x1C3, "u0041B8A0", 0x2),
    (0x1C4, "u00415720", 0x1),
    (0x1C5, "u00425800", 0x4),
    (0x1C6, "u0041DD80", 0x2),
    (0x1C7, "u00414F90", 0x1),
    (0x1C8, "toString", 0x2),  # u00425680 : toString
    (0x1C9, "u0041B8E0", 0x3),
    (0x1CA, "u0041B9B0", 0x1),
    (0x1CB, "u00414FD0", 0x1),
    (0x1CC, "u00415010", 0x1),
    (0x1CD, "u0041A560", 0x2),
    (0x1CE, "u0041B9F0", 0x1),
    (0x1CF, "u0041DA10", 0x1),
    (0x1D0, "u0041BA80", 0x3),
    (0x1D1, "u0041BAE0", 0x5),
    (0x1D2, "u0041BB40", 0x2),
    (0x1D3, "u0041BB90", 0x5),
    (0x1D4, "u0041BC00", 0x4),
    (0x1D5, "u00415700", 0x0),
    (0x1D6, "u0041DA40", 0x2),
    (0x1D7, "u0041DA80", 0x2),
    (0x1D8, "u0041DAD0", 0x3),
    (0x1D9, "u0041DB20", 0x2),
    (0x1F4, "u004160D0", 0x0),
    (0x1F5, "u00416120", 0x0),
    (0x1F6, "u00416170", 0x0),
    (0x1F7, "u00420270", 0x2),
    (0x1F8, "create-texture", 0x4),  # create a new drawable rect. param1 = id, param2 = sizeX, param3 = sizeY, param4 = ukn
    (0x1F9, "set-texture", 0x3),  # set a texture to a given ID. param1 = file index, param2 = id, param3 = ?
    (0x1FA, "u00420480", 0x1),
    (0x1FB, "draw-texture", 0x8),  # draw a texture. param1 = UI element id?, param2 = textureID, param3 = texX, param4 = texY, param5 = width, param6 = height, param7 = drawX, param8 = drawY
    (0x1FC, "u004205F0", 0x1),
    (0x1FD, "u00420620", 0x4),
    (0x1FE, "u004206C0", 0x5),
    (0x1FF, "u00420770", 0x4),
    (0x200, "u00420800", 0x1),
    (0x201, "u00416190", 0x1),
    (0x202, "u00420880", 0x5),
    (0x203, "u00420950", 0x4),
    (0x204, "draw-string", 0x4),  # u00420A10 : place-string. param1 = id? param2 = x, param3 = y, param4 = string
    (0x205, "u00420A60", 0x6),
    (0x206, "u004161C0", 0x7),
    (0x207, "u00420B00", 0x8),
    (0x208, "u00420BF0", 0x3),
    (0x209, "u00420C50", 0x5),
    (0x20A, "u00420CE0", 0x1),
    (0x20B, "u00420D50", 0x7),
    (0x20C, "u00416200", 0x0),
    (0x20D, "u00420E10", 0x1),
    (0x20E, "u00416250", 0x0),
    (0x20F, "u00420E40", 0x3),
    (0x210, "u00420FF0", 0x1),
    (0x211, "u00421060", 0x1),
    (0x212, "u00421090", 0x2),
    (0x213, "u004210D0", 0x3),
    (0x214, "u00421120", 0x2),
    (0x215, "u00421160", 0x2),
    (0x216, "u004211A0", 0x2),
    (0x217, "u004211E0", 0x4),
    (0x218, "u00421270", 0x4),
    (0x219, "u004212E0", 0x4),
    (0x21A, "u00421370", 0x4),
    (0x21B, "u004213E0", 0x1),
    (0x21C, "u00416270", 0x0),
    (0x21D, "u00421410", 0x2),
    (0x21E, "u00421450", 0x6),
    (0x21F, "u00421510", 0x7),
    (0x220, "u004215D0", 0x6),
    (0x221, "u00421670", 0x4),
    (0x222, "u004216C0", 0x2),
    (0x223, "u00421700", 0x8),
    (0x224, "u00416290", 0x0),
    (0x225, "u00421780", 0x2),
    (0x226, "u004217D0", 0x5),
    (0x227, "u00421880", 0x6),
    (0x228, "u00421940", 0x5),
    (0x229, "u004219E0", 0x5),
    (0x22A, "u00421A90", 0x3),
    (0x22B, "u00421B30", 0x4),
    (0x22C, "u00421BD0", 0x3),
    (0x22D, "u00421C60", 0x5),
    (0x22E, "u00421D10", 0x6),
    (0x22F, "u00421DD0", 0x5),
    (0x230, "u00421E70", 0x1),
    (0x231, "u00421EA0", 0x4),
    (0x232, "u00421EF0", 0x4),
    (0x233, "u00421FB0", 0x5),
    (0x234, "u00422060", 0x5),
    (0x235, "u00422100", 0x5),
    (0x236, "u004221A0", 0x4),
    (0x237, "u00422350", 0x2),
    (0x238, "u00422390", 0x1),
    (0x239, "u004223C0", 0x6),
    (0x23A, "u00422420", 0x2),
    (0x23B, "u00422460", 0x7),
    (0x23C, "u004162B0", 0x0),
    (0x23D, "u004162F0", 0x0),
    (0x23E, "u004228C0", 0x2),
    (0x23F, "u00422930", 0x2),
    (0x240, "u004229A0", 0x4),
    (0x241, "u00422B80", 0x5),
    (0x242, "u00422D60", 0x2),
    (0x243, "u00417070", 0x0),
    (0x244, "u00416360", 0x0),
    (0x245, "u00422DA0", 0x2),
    (0x246, "u00422E10", 0x2),
    (0x247, "u00416390", 0x1),
    (0x248, "u00422E80", 0x1),
    (0x249, "u00422EB0", 0x3),
    (0x24A, "u004163C0", 0x3),
    (0x24D, "u00422E90", 0xC),
    (0x24E, "u00422EA0", 0x1),
    (0x24F, "u00422ED0", 0xA),
    (0x250, "u00422F60", 0xA),
    (0x251, "u00422FF0", 0xC),
    (0x252, "u00423000", 0x1),
    (0x253, "u00423019", 0x2),
    (0x254, "u00423049", 0x5),
    (0x256, "u00423050", 0x5),
    (0x257, "257", 0x5),  # Sankai no Yubiwa
    (0x258, "u00422FE0", 0x2),
    (0x259, "u00416410", 0x0),
    (0x25A, "u00423120", 0x1),
    (0x25B, "25B", 0x1),  # Kami no Rhapsody
    (0x25C, "u00423122", 0x8),
    (0x25D, "u00423123", 0x3),
    (0x25E, "u00423124", 0x5),
    (0x25F, "u00423125", 0x4),
    (0x260, "u00423126", 0x4),
    (0x261, "u00423127", 0x1),
    (0x262, "262", 0x1),  # Amayui 2
    (0x263, "263", 0x1),  # Amayui 2
    (0x2BC, "u00423020", 0xB),
    (0x2BD, "u00423100", 0x1),
    (0x2BE, "u00423140", 0x1),
    (0x2BF, "u00423180", 0x3),
    (0x2C0, "u004231C0", 0x3),
    (0x2C1, "u00425BC0", 0x1),
    (0x2C2, "u00425CD0", 0x6),
    (0x2C3, "u00423200", 0x2),
    (0x2C4, "u00416450", 0x0),  # using as a way to test logging, originally u00416450
    (0x2C5, "strlen", 0x2),  # u0042B5D0 : strlen. param1 = param2.length()
    (0x2C6, "u0042B5E0", 0x2),
    (0x2C7, "u0042B5F0", 0x4),
    (0x2C8, "u0042B610", 0x4),
    (0x2C9, "2C9", 0x3),  # Sankai no Yubiwa
    (0x2CC, "2CC", 0x1),  # Sankai no Yubiwa
    (0x2CD, "2CD", 0x1),  # Sankai no Yubiwa
    (0x2CE, "u0042B616", 0x1),
    (0x2CF, "u0042B617", 0x1),
    (0x2D0, "u0042B940", 0x3),
    (0x2D1, "u0042B950", 0x3),
    (0x2D2, "u0042B960", 0x3),
    (0x2D3, "u0042B970", 0x3),
    (0x2D5, "u0042B990", 0x2),
    (0x2D7, "u0042B9B0", 0x2),
    (0x2D8, "set-array-to", 0x3),  # Set a given array to the given value x times. loop: param1[param3] = param2; param3++
    (0x2D9, "u0042BA30", 0x2),
    (0x2DA, "u004234E0", 0x8),
    (0x2DB, "u004235C0", 0x1),
    (0x2DC, "u0042BA80", 0x1),
    (0x2DD, "u0042D880", 0x2),
    (0x2DE, "u0042BAC0", 0x2),
    (0x2DF, "u0042BAC1", 0x3),
    (0x2E0, "u0042CE0F", 0x3),
    (0x2E1, "u0042CE10", 0x3),
    (0x2E2, "u0042CE11", 0x3),
    (0x2E3, "u0042CE30", 0x3),
    (0x2E4, "u0042CE31", 0x3),
    (0x2E5, "u0042CE50", 0x1),
    (0x2E6, "u0042CE60", 0x2),
    (0x2E7, "u0042CE70", 0x2),
    (0x2E8, "u0042CE80", 0x1),
    (0x2E9, "u0042CE90", 0x1),
    (0x2EA, "u0042CEA0", 0x1),
    (0x2EB, "u0042CEB0", 0x1),
    (0x2EC, "u0042CEC0", 0x2),
    (0x2EE, "u0042CEC2", 0x1),
    (0x2EF, "u0042CEC3", 0xB),
    (0x2F0, "u0042CEC4", 0x9),
    (0x2F1, "u0042CEC5", 0x7),
    (0x2F2, "u0042CEC6", 0x6),
    (0x2F3, "2F3", 0x6),  # La Dea
    (0x2F4, "2F4", 0x3),  # La Dea
    (0x2F5, "2F5", 0x4),  # La Dea
    (0x2F6, "2F6", 0x1),  # La Dea
    (0x2F7, "2F7", 0x1),  # La Dea
    (0x2F8, "2F8", 0x2),  # La Dea
    (0x2F9, "2F9", 0x7),  # La Dea
    (0x2FA, "2FA", 0x1),  # La Dea
    (0x2FB, "2FB", 0x1),  # La Dea
    (0x2FC, "2FC", 0x5),  # Kami no Rhapsody
    (0x2FD, "2FD", 0x6),  # Kami no Rhapsody
    (0x2FE, "2FE", 0x1),  # Sankai no Yubiwa
    (0x2FF, "2FF", 0x2),  # Sankai no Yubiwa
    (0x300, "300", 0x3),  # Sankai no Yubiwa
    (0x301, "301", 0x1),  # Sankai no Yubiwa
    (0x302, "302", 0x2),  # Sankai no Yubiwa
    (0x303, "303", 0x3),  # Sankai no Yubiwa
    (0x304, "304", 0x0),  # Sankai no Yubiwa
    (0x305, "305", 0x0),  # Sankai no Yubiwa
    (0x306, "306", 0x1),  # Sankai no Yubiwa
    (0x307, "307", 0x1),  # Sankai no Yubiwa
    (0x308, "308", 0x1),  # Amayui Alchemy Meister
    (0x30A, "30A", 0x2),  # Amayui Alchemy Meister
    (0x30C, "30C", 0x1),  # Tenmei no Conquista
    (0x320, "u0043AA20", 0xA),
    (0x321, "u0043AA30", 0x3),
    (0x322, "u0043AA40", 0x4),
    (0x323, "u0043AA50", 0x5),
    (0x324, "u0043AA60", 0x0),
    (0x325, "u0043AA70", 0x2),
    (0x326, "u0043AA80", 0x4),
    (0x327, "u0043AA90", 0x1),
    (0x328, "u0043AAA0", 0x3),
    (0x329, "u0043AAB0", 0x2),
    (0x32A, "32A", 0x1),  # Kami no Rhapsody
    (0x32B, "u0043AAD0", 0x0),
    (0x32C, "u0043AAE0", 0x6),
    (0x32D, "u0043AAF0", 0x2),
    (0x32E, "u0043AB10", 0xB),
    (0x32F, "u0043AB11", 0x1),
    (0x330, "u0043AB12", 0x2),
    (0x332, "u0043AB14", 0x4),
    (0x334, "u0043AB16", 0x1),
    (0x335, "u0043AB17", 0x4),
    (0x337, "u0043AB19", 0x4),
    (0x33B, "u0043AB1D", 0x4),
    (0x33D, "u0043AB1E", 0x3),
    (0x33E, "u0043AB1F", 0x5),
    (0x33F, "u0043AB20", 0x3),
    (0x340, "340", 0x1),  # Sankai no Yubiwa
    (0x341, "341", 0x2),  # Amayui Alchemy Meister
    (0x342, "342", 0x1),  # Amayui Alchemy Meister
    (0x344, "344", 0x2),  # Amayui Alchemy Meister
    (0x345, "345", 0x3),  # Amayui Alchemy Meister
    (0x349, "349", 0x4),  # Amayui Alchemy Meister
    (0x34D, "34D", 0x6),  # Amayui Alchemy Meister
    (0x34E, "34E", 0x4),  # Amayui Alchemy Meister
    (0x352, "352", 0x3),  # Amayui Alchemy Meister
    (0x353, "353", 0x2),  # Fuukan no Gransesta
    (0x354, "354", 0x2),  # Fuukan no Gransesta
    (0x358, "358", 0x5),  # Amayui 2
    (0x35A, "35A", 0x5),  # Amayui 2
    (0x35B, "35B", 0x2),  # Fuukan no Gransesta
    (0x35C, "35C", 0x2),  # Fuukan no Gransesta
    (0x35D, "35D", 0x3),  # Fuukan no Gransesta
    (0x35F, "35F", 0x3),  # Fuukan no Gransesta
    (0x360, "360", 0x3),  # Fuukan no Gransesta
    (0x361, "361", 0x2),  # Fuukan no Gransesta
    (0x363, "363", 0x3),  # Amayui 2
    (0x364, "364", 0x3),  # Amayui 2
    (0x384, "384", 0x3),  # Tenmei no Conquista
    (0x386, "386", 0xB),  # Tenmei no Conquista
    (0x387, "387", 0x8),  # Tenmei no Conquista
    (0x388, "388", 0x3),  # Tenmei no Conquista
    (0x389, "389", 0x6),  # Tenmei no Conquista
    (0x38F, "38F", 0x6),  # Tenmei no Conquista
    (0x390, "390", 0x7),  # Tenmei no Conquista
    (0x391, "391", 0x2),  # Amayui 2
    (0x392, "392", 0x1),  # Tenmei no Conquista
    (0x393, "393", 0x6),  # Amayui 2
    (0x396, "396", 0x5),  # Tenmei no Conquista
    (0x398, "398", 0x3),  # Amayui 2
    (0x399, "399", 0x7),  # Tenmei no Conquista
    (0x39B, "39B", 0x5),  # Amayui 2
]

# TODO check to see if the indexes are continuous to store them in a list
INSTRUCTION_DEFINITION_DICT = {
    definition_type: {
        'name': name,
        'number_of_arguments': number_of_arguments,
    } for (definition_type, name, number_of_arguments) in INSTRUCTION_DEFINITION_LIST
}

HEADER_SIZE = 60


def decompile_bin_file(
    inpath: str,
):
    infile = open(inpath, mode='rb')

    # file header format
    # 8 bytes: signature
    # uint32: int1
    # uint32: float1
    # uint32: string1
    # uint32: int2
    # uint32: unknown
    # uint32: string2
    # uint32: sub header size
    # uint32: table1 size
    # uint32: table1 offset
    # uint32: table2 size
    # uint32: table2 offset
    # uint32: table3 size
    # uint32: table3 offset

    header_content_bs = infile.read(HEADER_SIZE)
    real_header_size = len(header_content_bs)
    if real_header_size != HEADER_SIZE:
        raise Exception(f'Invalid BIN file! header size: {real_header_size}')

    # unpacking header
    header_content_unpack = struct.unpack('<8s13I', header_content_bs)
    header_content = {
        'signature_bs': header_content_unpack[0],
        'int1': header_content_unpack[1],
        'float1': header_content_unpack[2],
        'string1': header_content_unpack[3],
        'int2': header_content_unpack[4],
        'unknown': header_content_unpack[5],
        'string2': header_content_unpack[6],
        'sub_header_size': header_content_unpack[7],
        'table1_size': header_content_unpack[8],
        'table1_offset': header_content_unpack[9],
        'table2_size': header_content_unpack[10],
        'table2_offset': header_content_unpack[11],
        'table3_size': header_content_unpack[12],
        'table3_offset': header_content_unpack[13],
    }

    smallest_table_offset = min(
        header_content['table1_offset'],
        header_content['table2_offset'],
        header_content['table3_offset'],
    )

    # TODO rename this variable
    data_array_end = HEADER_SIZE + smallest_table_offset*4  # it seems that the data is stored in 4 byte chunks
    instruction_list = []

    while True:
        current_offset = infile.tell()
        if current_offset >= data_array_end:
            break  # TODO why
        # read an uint32 for instruction type
        instruction_type_bs = infile.read(4)
        if len(instruction_type_bs) != 4:
            raise Exception(f'failed to parse instruction type {inpath} at offset {current_offset}! len(instruction_type_bs) = {len(instruction_type_bs)}')
        instruction_type_int = struct.unpack('<I', instruction_type_bs)[0]
        if instruction_type_int not in INSTRUCTION_DEFINITION_DICT:
            raise Exception(f'Unknown instruction type {instruction_type_int} at offset {current_offset}')
        instruction_info = INSTRUCTION_DEFINITION_DICT[instruction_type_int]
        retval = parse_instruction(
            infile=infile,
            instruction_type_int=instruction_type_int,
            instruction_info=instruction_info,
            data_array_end=data_array_end,
        )

        data_array_end = retval['data_array_end']

        instruction_obj = {
            'offset': current_offset,
            'type': instruction_type_int,
            'name': instruction_info['name'],
            'argument_list': retval['argument_list'],
        }

        instruction_list.append(instruction_obj)

    infile.close()

    return {
        'header_content': header_content,
        'instruction_list': instruction_list,
    }


ARGUMENT_STRING_TYPE = 2


def parse_instruction(
    infile: io.BufferedWriter,
    instruction_type_int: int,
    instruction_info: dict,
    data_array_end: int,  # wtf is this
):
    number_of_arguments = instruction_info['number_of_arguments']
    argument_list = []
    for i in range(number_of_arguments):
        argument_offset = infile.tell()
        argument_type_bs = infile.read(4)
        if len(argument_type_bs) != 4:
            raise Exception(f'failed to get argument type for argument #{i} len(argument_type_bs) = {len(argument_type_bs)}')
        argument_type_int = struct.unpack('<I', argument_type_bs)[0]
        arugument_raw_data_bs = infile.read(4)
        if len(arugument_raw_data_bs) != 4:
            raise Exception(f'failed to get argument raw data for argument #{i} len(arugument_raw_data_bs) = {len(arugument_raw_data_bs)}')

        range1_condition = argument_type_int < 0
        range2_condition = (argument_type_int > 0xe) and (argument_type_int < 0x8003)
        range3_condition = argument_type_int > 0x800B

        if range1_condition or range2_condition or range3_condition:
            raise Exception(f'Unknown argument type {argument_type_int} at offset {argument_offset}')

        # 'String' or 'copy-array' arguments
        if argument_type_int == ARGUMENT_STRING_TYPE:
            string_offset = HEADER_SIZE + struct.unpack('<I', arugument_raw_data_bs)[0]*4
            # TODO can we put the HEADER_SIZE out of the offset calculation?
            data_array_end = min(data_array_end, string_offset)  # TODO why?
            backup_current_offset = infile.tell()

            # strings are all located at the end of the data array, XORed with 0xFF, and separated by 0xFF
            infile.seek(string_offset)

            string_byte_list = []
            while True:
                bs = infile.read(1)
                if len(bs) != 1:
                    raise Exception(f'failed to read string at offset {string_offset}! len(current_byte_value) = {len(current_byte_value)}')
                current_byte_value = bs[0]
                if current_byte_value == 0xFF:
                    break
                # XOR with 0xFF
                decoded_value = current_byte_value ^ 0xFF
                string_byte_list.append(decoded_value)
            # conver the list to bytes
            string_bs = bytes(string_byte_list)

            # restore the file pointer
            infile.seek(backup_current_offset)

            argument_list.append({
                'type': argument_type_int,
                'raw_data': arugument_raw_data_bs,
                'argument_offset': argument_offset,
                'string_bs': string_bs,
            })
        elif (instruction_type_int == 0x64) and (i == 1):
            # this instruction actually references an array in the file's footer
            array_offset = HEADER_SIZE + struct.unpack('<I', arugument_raw_data_bs)[0]*4
            data_array_end = min(data_array_end, array_offset)  # TODO why?
            backup_current_offset = infile.tell()

            infile.seek(array_offset)
            # the first 4 bytes indicate the data size
            array_length_bs = infile.read(4)
            if len(array_length_bs) != 4:
                raise Exception(f'failed to get array size at offset {array_offset}! len(array_length_bs) = {len(array_length_bs)}')
            array_length = struct.unpack('<I', array_length_bs)[0] * 4
            data_bs = infile.read(array_length)
            if len(data_bs) != array_length:
                raise Exception(f'failed to read array size at offset {array_offset}! len(data_bs) = {len(data_bs)} vs {array_length}')
            # TODO split the data into chunks of 4 bytes
            argument_list.append({
                'type': argument_type_int,
                'raw_data': arugument_raw_data_bs,
                'argument_offset': argument_offset,
                'array_length': array_length,
                'array_data': data_bs,
            })
        else:
            argument_list.append({
                'type': argument_type_int,
                'raw_data': arugument_raw_data_bs,
                'argument_offset': argument_offset,
            })

    return {
        'data_array_end': data_array_end,
        'instruction_type_int': instruction_type_int,
        'instruction_info': instruction_info,
        'argument_list': argument_list,
    }


def find_all_instructions_with_string_argument(
    instruction_list: list,
):
    retval = []
    for instruction_index in range(len(instruction_list)):
        instruction_info = instruction_list[instruction_index]
        for argument_index in range(len(instruction_info['argument_list'])):
            argument = instruction_info['argument_list'][argument_index]
            if argument['type'] == ARGUMENT_STRING_TYPE:
                retval.append((instruction_index, argument_index))
    return retval


def get_all_strings_data_from_find_results(
    find_results: list,
    instruction_list: list,
):
    retval = []
    for instruction_index, argument_index in find_results:
        retval.append(instruction_list[instruction_index]['argument_list'][argument_index]['string_bs'])
    return retval


def make_obj_json_friendly(obj):
    if isinstance(obj, (int, float, str)):
        return obj
    elif isinstance(obj, list):
        return [make_obj_json_friendly(x) for x in obj]
    elif isinstance(obj, dict):
        return {
            make_obj_json_friendly(k): make_obj_json_friendly(v) for k, v in obj.items()
        }
    else:
        return repr(obj)


def decompile_and_export_all_strings(
    inpath: str,
    outpath: str,
    force_decompile=False,
    force_strings=False,
):
    bin_filepath_list = []
    find_all_bin_files(inpath, bin_filepath_list)

    decompile_result_dir = os.path.join(outpath, 'decompiled')
    string_log_dir = os.path.join(outpath, 'strings')

    pbar = tqdm(bin_filepath_list)
    for bin_filepath in pbar:
        pbar.set_description(f'Processing {bin_filepath}')
        rel_path = os.path.relpath(bin_filepath, inpath)
        rel_parent, filename = os.path.split(rel_path)

        decompile_result_filename = f'{filename}.pickle'
        entry_decompile_result_dir = os.path.join(decompile_result_dir, rel_parent)
        decompile_result_filepath = os.path.join(entry_decompile_result_dir, decompile_result_filename)

        string_log_filename = f'{filename}.tsv'
        entry_string_log_dir = os.path.join(string_log_dir, rel_parent)
        string_log_filepath = os.path.join(entry_string_log_dir, string_log_filename)

        try:
            if os.path.exists(decompile_result_filepath) and not force_decompile:
                # load the decompile result
                with open(decompile_result_filepath, 'rb') as infile:
                    decompile_result = pickle.load(infile)
            else:
                decompile_result = decompile_bin_file(bin_filepath)
                # check if the file exists and the contents are the same
                pickle_content_bs = pickle.dumps(decompile_result)
                if os.path.exists(decompile_result_filepath):
                    original_bs = open(decompile_result_filepath, 'rb').read()
                    if original_bs != pickle_content_bs:
                        with open(decompile_result_filepath, 'wb') as outfile:
                            outfile.write(pickle_content_bs)
                else:
                    # create the directory if it doesn't exist
                    if not os.path.exists(entry_decompile_result_dir):
                        os.makedirs(entry_decompile_result_dir)
                    with open(decompile_result_filepath, 'wb') as outfile:
                        outfile.write(pickle_content_bs)

                del pickle_content_bs

            if os.path.exists(string_log_filepath) and not force_strings:
                pass
            else:
                string_content_bs_location_list = find_all_instructions_with_string_argument(decompile_result['instruction_list'])
                if len(string_content_bs_location_list) > 0:
                    string_content_bs_list = get_all_strings_data_from_find_results(string_content_bs_location_list, decompile_result['instruction_list'])

                    string_log_list = []
                    for i in range(len(string_content_bs_list)):
                        string_log = {
                            'instruction_index': string_content_bs_location_list[i][0],
                            'argument_index': string_content_bs_location_list[i][1],
                        }

                        try:
                            string_log['decoded_string'] = string_content_bs_list[i].decode('cp932')
                            string_log['original_bytes_length'] = len(string_content_bs_list[i])
                        except Exception as decode_exception:
                            stack_trace = traceback.format_exc()
                            string_log['stack_trace'] = stack_trace
                            string_log['exception'] = decode_exception

                        string_log_list.append(string_log)

                    # export to tsv
                    # format (instruction_index, argument_index, unicode_string_length, python_string_quote, repr_decoded_string_with_quote_removed)

                    if not os.path.exists(entry_string_log_dir):
                        os.makedirs(entry_string_log_dir)
                    with open(string_log_filepath, 'wb') as outfile:
                        # write the header
                        header_str = '\t'.join([
                            'instruction_index',
                            'argument_index',
                            'unicode_string_length',
                            'python_string_quote',
                            'repr_decoded_string_with_quote_removed',
                        ])

                        outfile.write(header_str.encode('utf-8'))
                        outfile.write(b'\n')

                        for string_log in tqdm(string_log_list, leave=False, desc=f'Writing {string_log_filepath}'):
                            if 'decoded_string' not in string_log:
                                continue

                            decoded_string = string_log['decoded_string']
                            unicode_string_length = len(decoded_string)
                            if unicode_string_length == 0:
                                continue

                            repr_decoded_string = repr(string_log['decoded_string'])
                            quote_char = repr_decoded_string[0]
                            repr_decoded_string_with_quote_removed = repr_decoded_string[1:-1]
                            line_str = '\t'.join([
                                str(string_log['instruction_index']),
                                str(string_log['argument_index']),
                                str(unicode_string_length),
                                quote_char,
                                repr_decoded_string_with_quote_removed,
                            ])

                            outfile.write(line_str.encode('utf-8'))
                            outfile.write(b'\n')
        except Exception as ex:
            print(bin_filepath)
            print(ex)


def main():
    parser = argparse.ArgumentParser(description='Decompile and export all strings from a directory of .bin files.')
    parser.add_argument('inpath', help='The directory to search for .bin files.')
    parser.add_argument('outpath', help='The directory to write the decompiled .bin files and the string logs to.')
    parser.add_argument('--force-decompile', action='store_true', help='Force decompilation of all .bin files.')
    parser.add_argument('--force-strings', action='store_true', help='Force exporting of all strings.')

    args = parser.parse_args()
    print('args', args)

    decompile_and_export_all_strings(
        args.inpath,
        args.outpath,
        force_decompile=args.force_decompile,
        force_strings=args.force_strings,
    )


if __name__ == '__main__':
    main()
