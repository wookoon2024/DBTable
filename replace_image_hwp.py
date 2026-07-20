import shutil
import os
import olefile
from PIL import Image, ImageDraw

# Search for '시.hwp' by file size (388096 bytes) to bypass filename encoding issues
src_hwp = None
for f in os.listdir('.'):
    if os.path.isfile(f) and os.path.getsize(f) == 388096:
        src_hwp = f
        break

if not src_hwp:
    # Fallback to any .hwp file that is not 'replaced'
    for f in os.listdir('.'):
        if f.lower().endswith('.hwp') and 'replaced' not in f.lower():
            src_hwp = f
            break

if not src_hwp:
    raise FileNotFoundError("Could not find the original 시.hwp file!")

dst_hwp = 'test_binary_replaced_v2.hwp'

# 1. Copy original HWP
print(f"Copying original HWP file ({src_hwp}) to {dst_hwp}...")
shutil.copy2(src_hwp, dst_hwp)
print(f"Copied successfully.")

# 2. Open OLE file and check target stream size
ole = olefile.OleFileIO(dst_hwp, write_mode=True)
target_stream = 'BinData/BIN0001.png'
target_size = ole.get_size(target_stream)
print(f"Target stream '{target_stream}' size: {target_size} bytes")

# 3. Generate a new custom PNG image
img_temp_path = 'temp_new_img.png'
print("Generating new PNG image (smiley face) using PIL...")
# Create a green background
img = Image.new('RGB', (800, 600), color='#10B981')
draw = ImageDraw.Draw(img)

# Draw a yellow circle (face)
draw.ellipse([(250, 100), (550, 400)], fill='#FBBF24', outline='#D97706', width=4)
# Draw eyes
draw.ellipse([(320, 180), (360, 220)], fill='#1F2937')
draw.ellipse([(440, 180), (480, 220)], fill='#1F2937')
# Draw mouth
draw.arc([(320, 220), (480, 320)], start=0, end=180, fill='#1F2937', width=6)

# Draw white borders
draw.rectangle([(10, 10), (790, 590)], outline='#FFFFFF', width=6)
# Draw text
draw.text((250, 480), "[ THIS IS A REAL EMBEDDED IMAGE ]", fill='#FFFFFF')
img.save(img_temp_path, 'PNG')

# 4. Read image bytes
with open(img_temp_path, 'rb') as f:
    img_bytes = f.read()
os.remove(img_temp_path)

current_size = len(img_bytes)
print(f"Generated PNG size: {current_size} bytes")

if current_size > target_size:
    raise ValueError("Generated image is too large! Must be smaller than target stream size.")

# 5. Pad the image bytes to match the exact stream size
padding_needed = target_size - current_size
padded_bytes = img_bytes + b'\x00' * padding_needed
print(f"Padded data size: {len(padded_bytes)} bytes (added {padding_needed} null bytes)")

# 6. Overwrite the stream in the compound HWP file
print("Overwriting OLE stream inside HWP...")
ole.write_stream(target_stream, padded_bytes)
ole.close()
print("OLE stream overwritten successfully!")
print(f"Final HWP file size: {os.path.getsize(dst_hwp)} bytes")
