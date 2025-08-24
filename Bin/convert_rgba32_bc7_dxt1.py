import ctypes
import os
import re
import struct

from PIL import Image

NAME_PATTERN = re.compile(r"^(.+?)-(CAB-[0-9a-f]{32}|BuildPlayer-.+\.sharedAssets)-(-?\d+)")
INPUT_FOLDERS = [
  "input",
  "input-bc7",
  "input-dxt1",
]


dll = ctypes.CDLL("Bin/TexToolWrap.dll")
dll.EncodeByISPC.argtypes = [
  ctypes.c_void_p,  # data
  ctypes.c_void_p,  # outBuf
  ctypes.c_int,  # mode
  ctypes.c_int,  # level
  ctypes.c_uint,  # width
  ctypes.c_uint,  # height
]
dll.EncodeByISPC.restype = ctypes.c_uint


def encode_data(data: bytes, mode: int, level: int, width: int, height: int) -> bytes:
  in_buf = ctypes.create_string_buffer(data)
  in_ptr = ctypes.addressof(in_buf)

  out_size = len(data) * 4
  out_buf = ctypes.create_string_buffer(out_size)
  out_ptr = ctypes.addressof(out_buf)

  result_len = dll.EncodeByISPC(
    in_ptr, out_ptr, ctypes.c_int(mode), ctypes.c_int(level), ctypes.c_uint(width), ctypes.c_uint(height)
  )

  return bytes(out_buf[:result_len])


for folder in os.listdir("Images"):
  if "CAB-" not in folder and ".sharedAssets" not in folder:
    continue
  for input_folder in INPUT_FOLDERS:
    if not os.path.exists(f"Images/{folder}/{input_folder}"):
      continue
    for file_name in os.listdir(f"Images/{folder}/{input_folder}"):
      if not file_name.endswith(".png"):
        continue

      if not NAME_PATTERN.match(file_name):
        continue

      image_name, cab_id, index = NAME_PATTERN.match(file_name).groups()
      index = int(index)
      index_hex = struct.pack(">q", index).hex().zfill(16)

      image = Image.open(f"Images/{folder}/{input_folder}/{file_name}")

     # --- 通用的预处理和检查代码块 ---
     # 只要是需要调用DLL进行压缩的文件夹，都在这里检查
      if input_folder in ["input-dxt1", "input-bc7"]:
        # 1. 检查尺寸是否为4的倍数 (DXT/BC 压缩的硬性要求)
        if image.width % 4 != 0 or image.height % 4 != 0:
          print(f"[ERROR] Image '{file_name}' in '{input_folder}' has dimensions ({image.width}x{image.height}) not a multiple of 4. Skipping.")
          continue  # 跳过这个不符合要求的文件，防止崩溃

        # 2. 统一颜色模式为 RGBA，确保数据格式正确
        if image.mode != "RGBA":
          print(f"[INFO] Converting image '{file_name}' from mode '{image.mode}' to 'RGBA'.")
          image = image.convert("RGBA")
     # --- 检查代码块结束 ---
      
      image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
      image_bytes = image.tobytes("raw")
      if input_folder == "input-bc7":
        print(f"Processing BC7 for '{file_name}' ({image.width}x{image.height})...")
        image_bytes = encode_data(image_bytes, 25, 5, image.width, image.height)
      elif input_folder == "input-dxt1":
        print(f"Processing DXT1 for '{file_name}' ({image.width}x{image.height})...")
        image_bytes = encode_data(image_bytes, 10, 5, image.width, image.height)

      output_path = f"Patch/{cab_id}/Texture2D/{index_hex}.res"
      os.makedirs(os.path.dirname(output_path), exist_ok=True)
      with open(output_path, "wb") as output_file:
        output_file.write(image_bytes)
      print(f"Processed {cab_id}/{image_name} -> {output_path}")
