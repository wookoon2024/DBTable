import os

dir_path = os.path.dirname(os.path.abspath(__file__))

def list_all_files(folder_name):
    target_dir = os.path.join(dir_path, folder_name)
    if not os.path.exists(target_dir):
         # Try finding the folder by matching name prefix in case of encoding issues
         for d in os.listdir(dir_path):
             if d.startswith(folder_name) or (folder_name == '시' and (d == '시' or len(d) == 1 and ord(d) > 256)):
                 target_dir = os.path.join(dir_path, d)
                 break
    
    print(f"\n=== Folder: {folder_name} ({os.path.basename(target_dir)}) ===")
    if not os.path.exists(target_dir):
        print("Folder not found!")
        return {}
        
    structure = {}
    for root, dirs, files in os.walk(target_dir):
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, target_dir)
            size = os.path.getsize(full_path)
            structure[rel_path] = size
            print(f"- {rel_path}: {size} bytes")
    return structure

struct_v2 = list_all_files('test_sample_image_v2')
struct_si = list_all_files('시')
