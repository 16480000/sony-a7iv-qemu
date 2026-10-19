"""Read original DMM extent/unit metadata using dmm.ko's serialized layout."""
import struct

def parse(raw):
    cursor=0
    def take(size):
        nonlocal cursor
        if cursor+size>len(raw):raise ValueError('Truncated DMM configuration')
        offset=cursor;cursor+=size
        return offset,raw[offset:cursor]
    extents=[]
    # dmm_ext_tbl_Init: root extents, then allocation-rule extent groups.
    # Each category has80-byte group headers; header+8=-1 terminates it.
    for category in range(2):
        for group in range(1024):
            header_offset,header=take(80)
            if struct.unpack_from('<I',header,8)[0]==0xffffffff:break
            for index in range(65536):
                offset,data=take(20);words=struct.unpack('<5I',data)
                if words[2]==0xffffffff:break
                extents.append({'category':category,'group':group,'file_offset':offset,
                    'words':list(words),'extent_id':words[2],'unit_size':words[3]})
            else:raise ValueError('Unterminated DMM extent group')
        else:raise ValueError('Unterminated DMM extent category')
    table_start=cursor
    first={}
    for row in extents:first.setdefault(row['extent_id'],row)
    units=[]
    # dmm_unit_tbl_Init:8-byte header, then4-byte extent IDs until-1.
    # dmm_unit_ctrl_GetUnitSize uses the first extent ID only.
    for index in range(4096):
        offset,data=take(8);key,reserved=struct.unpack('<2I',data)
        if key==0xffffffff:break
        ids=[]
        for _ in range(4096):
            _,data=take(4);extent=struct.unpack('<I',data)[0]
            if extent==0xffffffff:break
            ids.append(extent)
        else:raise ValueError('Unterminated DMM unit extent list')
        if not ids:raise ValueError('Empty DMM unit extent list')
        row=first.get(ids[0])
        units.append({'unit_type':key,'reserved':reserved,'file_offset':offset,
            'extent_ids':ids,'first_extent_file_offset':row['file_offset'] if row else None,
            'unit_size':row['unit_size'] if row else 0})
    else:raise ValueError('Unterminated DMM unit table')
    return {'extents':extents,'units':units,'unit_table_start':table_start,
            'unit_table_end':cursor,'unparsed_version_tail_bytes':len(raw)-cursor}
