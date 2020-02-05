import re
import ctypes
import struct
from os import path
from glob import glob
from argparse import ArgumentParser
from winreg import ConnectRegistry, HKEY_LOCAL_MACHINE, OpenKeyEx, QueryValueEx

BUFFER_SIZE = 1024

GetSystemMetrics = ctypes.windll.user32.GetSystemMetrics
GetLongPathNameW = ctypes.windll.kernel32.GetLongPathNameW


def get_sof2_path():
    try:
        root = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
        policy_key = OpenKeyEx(root, r"SOFTWARE\WOW6432Node\Activision\Soldier of Fortune II - Double Helix")
        result, _type = QueryValueEx(policy_key, "InstallPath")
        buffer = ctypes.create_unicode_buffer(BUFFER_SIZE)
        GetLongPathNameW(result, buffer, BUFFER_SIZE)
        return buffer.value
    except OSError:
        return None


def bytes_to_int(value):
    return struct.unpack("<I", value)[0]


class SoF2(object):
    def __init__(self, file_path="SoF2MP.exe"):
        self.file_path = file_path
        with open(self.file_path, "rb") as f:
            self.file_content = f.read()
        self.base_address = bytes_to_int(self.file_content[0x12C:0x130])

    def patch_resolution(self, width=GetSystemMetrics(0), height=GetSystemMetrics(1)):
        # Find Resolution String
        offset = self.file_content.find(b"Mode  3: 640x480")
        if not offset:
            raise Exception("Resolution String Not Found!")

        # Find Resolution String Reference
        string_reference = struct.pack("<L", self.base_address + offset)
        result = re.search(string_reference + br"(?P<width>.{4})(?P<height>.{4})\x00\x00\x80\x3F", self.file_content)
        if not result:
            raise Exception("Resolution Reference Not Found!")

        print(f"Resolution Found: {bytes_to_int(result.group('width'))}, {bytes_to_int(result.group('height'))}.")

        # Replace Resolution To System Resolution
        replace_from = result.group(0)
        replace_to = replace_from.replace(
            result.group('width') + result.group('height'),
            struct.pack('<I', int(width)) + struct.pack('<I', int(height))
        )
        self.file_content = self.file_content.replace(replace_from, replace_to, 1)

        print(f"New Resolution: {width}, {height}.")

        return self.file_content

    def patch_logging(self):
        # Patch Logging Function
        results = list(re.finditer(
            br"\xB8\x00\x10\x00\x00"
            br"\xE8.{4}"
            br"\x8B\x8C\x24.\x10\x00\x00"
            br"\x8D\x84\x24.\x10\x00\x00"
            br"\x50"
            br"\x51"
            br"\x8D\x54\x24\x08"
            br"\x52"
            br"\xE8.{4}",
            self.file_content
        ))
        if results:
            for result in results:
                replace_from = result.group(0)
                replace_to = replace_from.replace(b'\xB8', b'\xC3', 1)
                self.file_content = self.file_content.replace(replace_from, replace_to, 1)
            print("Logging Function Patched")
        else:
            print("Logging Function Already Patched")

        return self.file_content

    def save(self, ext=""):
        with open(f"{self.file_path}{ext}", "wb") as f:
            f.write(self.file_content)

    def patch(self, save_backup=True, patch_log=True, patch_res=True, res_str=""):
        if save_backup:
            self.save(ext=".backup")

        if patch_log:
            self.patch_logging()

        if patch_res:
            kwargs = {}
            if res_str:
                re_res = re.search(r'(?P<width>\d+)\s*x\s*(?P<height>\d+)', res_str, re.IGNORECASE)
                kwargs = re_res.groupdict()
            self.patch_resolution(**kwargs)

        self.save()


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("-r", "--resolution",
                        help="resolution to patch (for example: 1920x1080)",
                        default="")
    parser.add_argument("-f", "--file",
                        help="file to patch",
                        nargs='+',
                        default=[])
    parser.add_argument("-nb", "--no-backup",
                        help="don't save .backup file",
                        action="store_true")
    parser.add_argument("-nlp", "--no-log-patch",
                        help="don't patch log function",
                        action="store_true")
    parser.add_argument("-nrp", "--no-resolution-patch",
                        help="don't patch resolution",
                        action="store_true")

    args = parser.parse_args()

    sof2_paths = args.file
    if not sof2_paths:
        sof2_paths = list(map(path.abspath, glob('./SoF2*.exe')))
    if not sof2_paths:
        sof2_paths = list(glob(path.join(get_sof2_path(), 'SoF2*.exe')))

    for sof2_path in sof2_paths:
        print("%s:" % path.abspath(sof2_path))
        sof2 = SoF2(file_path=sof2_path)
        sof2.patch(
            save_backup=not args.no_backup,
            patch_log=not args.no_log_patch,
            patch_res=not args.no_resolution_patch,
            res_str=args.resolution
        )
        print()
