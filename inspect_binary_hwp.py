import struct
import olefile
import zlib

def parse_records(data):
    records = []
    offset = 0
    length = len(data)
    while offset < length:
        if offset + 4 > length:
            break
        header = struct.unpack_from('<I', data, offset)[0]
        offset += 4
        
        tag_id = header & 0x3FF
        level = (header >> 10) & 0x3FF
        size = (header >> 20) & 0xFFF
        
        if size == 0xFFF:
            if offset + 4 > length:
                break
            size = struct.unpack_from('<I', data, offset)[0]
            offset += 4
            
        if offset + size > length:
            break
        record_data = data[offset:offset+size]
        offset += size
        
        records.append({
            'tag_id': tag_id,
            'level': level,
            'size': size,
            'data': record_data
        })
    return records

# Stream tags mapping for DocInfo and BodyText (offset by HWPTAG_BEGIN = 16)
HWPTAG_BEGIN = 16
docinfo_tags = {
    0 + HWPTAG_BEGIN: 'HWPTAG_DOCUMENT_PROPERTIES',
    1 + HWPTAG_BEGIN: 'HWPTAG_ID_MAPPINGS',
    2 + HWPTAG_BEGIN: 'HWPTAG_BIN_DATA',
    3 + HWPTAG_BEGIN: 'HWPTAG_FACE_NAME',
    4 + HWPTAG_BEGIN: 'HWPTAG_BORDER_FILL',
    5 + HWPTAG_BEGIN: 'HWPTAG_CHAR_SHAPE',
    6 + HWPTAG_BEGIN: 'HWPTAG_TAB_DEF',
    7 + HWPTAG_BEGIN: 'HWPTAG_NUMBERING',
    8 + HWPTAG_BEGIN: 'HWPTAG_BULLET',
    9 + HWPTAG_BEGIN: 'HWPTAG_PARA_SHAPE',
    10 + HWPTAG_BEGIN: 'HWPTAG_STYLE',
    11 + HWPTAG_BEGIN: 'HWPTAG_DOC_DATA',
    12 + HWPTAG_BEGIN: 'HWPTAG_DISTRIBUTE_DOC_DATA',
    13 + HWPTAG_BEGIN: 'HWPTAG_COMPATIBLE_DOCUMENT',
    14 + HWPTAG_BEGIN: 'HWPTAG_LAYOUT_COMPATIBILITY',
    15 + HWPTAG_BEGIN: 'HWPTAG_TRACKCHANGE',
    16 + HWPTAG_BEGIN: 'HWPTAG_MEMO_SHAPE',
    17 + HWPTAG_BEGIN: 'HWPTAG_FORBIDDEN_CHAR',
    18 + HWPTAG_BEGIN: 'HWPTAG_TRACK_CHANGE_AUTHOR'
}

bodytext_tags = {
    50 + HWPTAG_BEGIN: 'HWPTAG_PARA_HEADER',
    51 + HWPTAG_BEGIN: 'HWPTAG_PARA_TEXT',
    52 + HWPTAG_BEGIN: 'HWPTAG_PARA_CHAR_SHAPE',
    53 + HWPTAG_BEGIN: 'HWPTAG_PARA_LINE_ALIGN',
    54 + HWPTAG_BEGIN: 'HWPTAG_PARA_RANGE_TAG',
    55 + HWPTAG_BEGIN: 'HWPTAG_CTRL_HEADER',
    56 + HWPTAG_BEGIN: 'HWPTAG_LIST_HEADER',
    57 + HWPTAG_BEGIN: 'HWPTAG_PAGE_DEF',
    58 + HWPTAG_BEGIN: 'HWPTAG_FOOTNOTE_SHAPE',
    59 + HWPTAG_BEGIN: 'HWPTAG_PAGE_BORDER_FILL',
    60 + HWPTAG_BEGIN: 'HWPTAG_SHAPE_COMPONENT',
    61 + HWPTAG_BEGIN: 'HWPTAG_TABLE',
    62 + HWPTAG_BEGIN: 'HWPTAG_SHAPE_COMPONENT_LINE',
    63 + HWPTAG_BEGIN: 'HWPTAG_SHAPE_COMPONENT_RECTANGLE',
    64 + HWPTAG_BEGIN: 'HWPTAG_SHAPE_COMPONENT_ELLIPSE',
    65 + HWPTAG_BEGIN: 'HWPTAG_SHAPE_COMPONENT_ARC',
    66 + HWPTAG_BEGIN: 'HWPTAG_SHAPE_COMPONENT_POLYGON',
    67 + HWPTAG_BEGIN: 'HWPTAG_SHAPE_COMPONENT_CURVE',
    68 + HWPTAG_BEGIN: 'HWPTAG_SHAPE_COMPONENT_OLE',
    69 + HWPTAG_BEGIN: 'HWPTAG_SHAPE_COMPONENT_PICTURE',
    70 + HWPTAG_BEGIN: 'HWPTAG_SHAPE_COMPONENT_CONTAINER',
    71 + HWPTAG_BEGIN: 'HWPTAG_CTRL_DATA',
    72 + HWPTAG_BEGIN: 'HWPTAG_EQEDIT',
    75 + HWPTAG_BEGIN: 'HWPTAG_SHAPE_COMPONENT_TEXTART',
    76 + HWPTAG_BEGIN: 'HWPTAG_XML_TEMPLATE_START',
    77 + HWPTAG_BEGIN: 'HWPTAG_XML_TEMPLATE_END',
    78 + HWPTAG_BEGIN: 'HWPTAG_SHAPE_COMPONENT_UNKNOWN'
}

ole = olefile.OleFileIO('시.hwp')

print("=== DOCINFO RECORDS ===")
raw_docinfo = ole.openstream('DocInfo').read()
try:
    docinfo_data = zlib.decompress(raw_docinfo, -15)
except Exception:
    docinfo_data = raw_docinfo
docinfo_records = parse_records(docinfo_data)
for idx, r in enumerate(docinfo_records):
    tag_name = docinfo_tags.get(r['tag_id'], f"UNKNOWN_{r['tag_id']}")
    if tag_name in ('HWPTAG_DOCUMENT_PROPERTIES', 'HWPTAG_ID_MAPPINGS', 'HWPTAG_BIN_DATA'):
        print(f"Record {idx}: Tag={tag_name} ({r['tag_id']}), Level={r['level']}, Size={r['size']}")
        if tag_name == 'HWPTAG_BIN_DATA':
            # BinData format: property(WORD), absolute path (LPWSTR), relative path (LPWSTR)
            prop = struct.unpack_from('<H', r['data'], 0)[0]
            pos = 2
            # Absolute path length (characters)
            abs_len = struct.unpack_from('<H', r['data'], pos)[0]
            pos += 2
            abs_path = r['data'][pos:pos+abs_len*2].decode('utf-16le', errors='ignore')
            pos += abs_len*2
            # Relative path length
            rel_len = struct.unpack_from('<H', r['data'], pos)[0]
            pos += 2
            rel_path = r['data'][pos:pos+rel_len*2].decode('utf-16le', errors='ignore')
            print(f"  -> Property={hex(prop)}, AbsPath='{abs_path}', RelPath='{rel_path}'")

print("\n=== BODYTEXT/SECTION0 RECORDS ===")
raw_section = ole.openstream('BodyText/Section0').read()
try:
    section_data = zlib.decompress(raw_section, -15)
except Exception:
    section_data = raw_section
section_records = parse_records(section_data)
for idx, r in enumerate(section_records):
    tag_name = bodytext_tags.get(r['tag_id'], f"UNKNOWN_{r['tag_id']}")
    # Print interesting shape component records and controls
    if r['tag_id'] in (55 + HWPTAG_BEGIN, 60 + HWPTAG_BEGIN, 69 + HWPTAG_BEGIN, 71 + HWPTAG_BEGIN) or 'SHAPE' in tag_name:
        print(f"Record {idx}: Tag={tag_name} ({r['tag_id']}), Level={r['level']}, Size={r['size']}")
        if tag_name == 'HWPTAG_CTRL_HEADER':
            ctrl_id = r['data'][:4].decode('ascii', errors='ignore')[::-1]
            print(f"  -> Control ID={ctrl_id}")
        elif tag_name == 'HWPTAG_SHAPE_COMPONENT_PICTURE':
            print(f"  -> Data (hex)={r['data'].hex()}")
            # In HWP 5.0 picture tag, the BinData reference ID is usually at offset 44 (2 bytes)
            if len(r['data']) >= 46:
                bindata_id = struct.unpack_from('<H', r['data'], 44)[0]
                print(f"  -> Reference BinData ID={bindata_id}")

ole.close()
