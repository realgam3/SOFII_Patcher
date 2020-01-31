import re
import ctypes
import struct


def bytes_to_int(value):
    return struct.unpack("<I", value)[0]


sof2mp = open("SoF2MP.exe", "rb").read()

# Patch Logging Function
result = re.search(br"\xB8\x00\x10\x00\x00\xE8.{4}", sof2mp)
if result:
    replace_from = result.group(0)
    replace_to = replace_from.replace(b'\xB8', b'\xC3', 1)
    sof2mp = sof2mp.replace(replace_from, replace_to, 1)
    print("Logging Function Patched")
else:
    print("Logging Function Already Patched")

# Find Resolution String
offset = sof2mp.find(b"Mode  3: 640x480")
if not offset:
    raise Exception("Resolution String Not Found!")

# Find Resolution String Reference
base_address = 0x400000
string_reference = struct.pack("<L", base_address + offset)
result = re.search(string_reference + br"(?P<width>.{4})(?P<height>.{4})\x00\x00\x80\x3F", sof2mp)
if not result:
    raise Exception("Resolution Reference Not Found!")

print(f"Resolution Found: {bytes_to_int(result.group('width'))}, {bytes_to_int(result.group('height'))}.")

# Get System Resolution
GetSystemMetrics = ctypes.windll.user32.GetSystemMetrics
width, height = GetSystemMetrics(0), GetSystemMetrics(1)

# Replace Resolution To System Resolution
replace_from = result.group(0)
replace_to = replace_from.replace(
    result.group('width') + result.group('height'),
    struct.pack('<I', width) + struct.pack('<I', height)
)

# Save
open("SoF2MP.exe.backup", "wb").write(sof2mp)
open("SoF2MP.exe", "wb").write(sof2mp.replace(replace_from, replace_to, 1))

print(f"New Resolution: {width}, {height}.")
