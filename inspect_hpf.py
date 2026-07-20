import zipfile
import os

dir_path = os.path.dirname(os.path.abspath(__file__))
print("Script directory:", dir_path)
print("Files in directory:")
for f in os.listdir(dir_path):
    print("- ", f)
filepath = os.path.join(dir_path, 'test_sample_image_v2.hwpx')
print("Checking file:", filepath)
z = zipfile.ZipFile(filepath)

print("\n=== Compression Type of Files ===")
for info in z.infolist():
    # 0 = Stored (no compression), 8 = Deflated
    comp_name = "Stored" if info.compress_type == 0 else "Deflated"
    print(f"{info.filename}: {comp_name} ({info.file_size} bytes)")

if 'Contents/content.hpf' in z.namelist():
    content = z.read('Contents/content.hpf').decode('utf-8')
    print("\n=== content.hpf ===")
    print(content)
else:
    print("\ncontent.hpf NOT found!")
z.close()
