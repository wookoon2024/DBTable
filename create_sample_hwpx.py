import os
import base64
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw

# 1. Generate a sample JPEG image using PIL
img_path = 'sample_test_image.jpg'
print("Generating sample JPEG image...")
# Create a 400x200 image with a blue background and text
img = Image.new('RGB', (400, 200), color='#2563EB')
draw = ImageDraw.Draw(img)
# Draw a simple white rectangle border
draw.rectangle([(10, 10), (390, 190)], outline='#FFFFFF', width=3)
# Draw text
draw.text((100, 90), "HWPX IMAGE EMBED TEST", fill='#FFFFFF')
img.save(img_path, 'JPEG')
print(f"Sample image saved to: {img_path}")

# Load the image bytes
with open(img_path, 'rb') as f:
    img_bytes = f.read()

# 2. Setup python-hwpx and apply patches to ensure Hancom Viewer compatibility
from hwpx import HwpxDocument
import hwpx.templates
import hwpx.document

# Extract skeleton_b64 from biz_guide_app.py
with open('biz_guide_app.py', 'r', encoding='utf-8') as f:
    content = f.read()
import re
skeleton_match = re.search(r'skeleton_b64 = "([^"]+)"', content)
if skeleton_match:
    skeleton_b64 = skeleton_match.group(1)
else:
    raise ValueError("Could not find skeleton_b64 in biz_guide_app.py")

hwpx.templates.blank_document_bytes = lambda: base64.b64decode(skeleton_b64)
hwpx.document.blank_document_bytes = lambda: base64.b64decode(skeleton_b64)

# Patch 1: Correct the mapping of image IDs by setting isEmbeded="1" on manifest item
_orig_add_image = HwpxDocument.add_image
def patched_add_image(self, image_data, image_format, *, item_id=None):
    orig_item_id = _orig_add_image(self, image_data, image_format, item_id=item_id)
    try:
        manifest_el = self._package._manifest_element()
        if manifest_el is not None:
            for item in manifest_el:
                if item.tag.endswith('}item') and item.get('id') == orig_item_id:
                    item.set('isEmbeded', '1')
            self._package._persist_manifest()
    except Exception:
        pass
    return orig_item_id
HwpxDocument.add_image = patched_add_image

# Patch 2: Reconstruct META-INF/manifest.xml dynamically for OPC zip packaging
from hwpx.opc.package import HwpxPackage
_orig_save_to_zip = HwpxPackage._save_to_zip
def patched_save_to_zip(self, pkg_file, **kwargs):
    ns = "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"
    ET.register_namespace('odf', ns)
    root = ET.Element(f"{{{ns}}}manifest")
    ET.SubElement(root, f"{{{ns}}}file-entry", {
        f"{{{ns}}}full-path": "/",
        f"{{{ns}}}media-type": "application/vnd.hancom.hwpx"
    })
    for path in sorted(self._files.keys()):
        if path in ('mimetype', 'META-INF/manifest.xml'):
            continue
        ext = path.split('.')[-1].lower()
        if ext == 'xml': media_type = 'text/xml'
        elif ext == 'hpf': media_type = 'text/xml'
        elif ext in ('png', 'jpg', 'jpeg', 'gif'):
            media_type = f'image/{ext}'
            if ext == 'jpg': media_type = 'image/jpeg'
        elif ext == 'txt': media_type = 'text/plain'
        elif ext == 'rdf': media_type = 'application/rdf+xml'
        else: media_type = 'application/octet-stream'
        ET.SubElement(root, f"{{{ns}}}file-entry", {
            f"{{{ns}}}full-path": path,
            f"{{{ns}}}media-type": media_type
        })
    xml_data = ET.tostring(root, encoding='utf-8', xml_declaration=True)
    xml_str = xml_data.decode('utf-8').replace(
        "<?xml version='1.0' encoding='utf-8'?>",
        '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
    )
    self._files['META-INF/manifest.xml'] = xml_str.encode('utf-8')
    return _orig_save_to_zip(self, pkg_file, **kwargs)
HwpxPackage._save_to_zip = patched_save_to_zip

# 3. Create document and add content
print("Creating HwpxDocument...")
doc = HwpxDocument.new()

# Add Title
p1 = doc.add_paragraph('')
p1.add_run("HWPX 이미지 내장 테스트 문서", bold=True, size=20)

# Add Description
doc.add_paragraph("아래에 생성된 파란색 테스트 이미지(JPEG)가 표시됩니다.")
doc.add_paragraph("=" * 50)

# Embed image (using 75 hwpunit = 1px standard)
# 400px width -> 30000 hwpunit, 200px height -> 15000 hwpunit
try:
    binary_id = doc.add_image(img_bytes, 'jpeg')
    p3 = doc.add_paragraph('')
    p3.add_picture(binary_id, width=30000, height=15000)
    print(f"Image added successfully with binary ID: {binary_id}")
except Exception as e:
    print(f"Error adding image to document: {e}")

out_hwpx = 'test_sample_image_v2.hwpx'
doc.save_to_path(out_hwpx)
print(f"Sample HWPX saved to: {os.path.abspath(out_hwpx)}")

# Clean up temp files
if os.path.exists(img_path):
    os.remove(img_path)
