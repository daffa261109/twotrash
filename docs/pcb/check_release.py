"""Check exported scale, mirror orientation, documentation links and release hashes."""
from pathlib import Path
import csv, hashlib, json, re
import numpy as np
import pymupdf
ROOT=Path(__file__).resolve().parent
MM=72/25.4

def main():
    board=json.loads((ROOT/'board.json').read_text())
    drc=json.loads((ROOT/'drc-report.json').read_text())
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    assert drc['passed'] and drc['board_sha256']==digest(ROOT/'board.json')
    paths=sorted((ROOT/'output/pdf').glob('*.pdf'))
    assert len(paths)==4
    pages=0
    for path in paths:
        doc=pymupdf.open(path);pages+=len(doc)
        expected=(420,297) if path.name.startswith('04') else (210,297)
        for p in doc:
            assert abs(p.rect.width/MM-expected[0])<.02 and abs(p.rect.height/MM-expected[1])<.02
            for block in p.get_text('dict')['blocks']:
                for line in block.get('lines',[]):
                    for span in line['spans']:
                        assert p.rect.contains(pymupdf.Rect(span['bbox'])),(path.name,span['text'])
        if path.name.startswith(('01','02')):
            found=[]
            for drawing in doc[0].get_drawings():
                for item in drawing['items']:
                    if item[0]=='l':
                        a,b=item[1:]
                        if abs(a.y-(297-132)*MM)<.01 and abs(b.y-a.y)<.01 and abs(a.x-35*MM)<.01:
                            found.append(abs(b.x-a.x)/MM)
            assert found and abs(found[0]-50)<.001
    def copper(path):
        p=pymupdf.open(path)[0]
        pix=p.get_pixmap(matrix=pymupdf.Matrix(2,2),clip=pymupdf.Rect(35*MM,52*MM,175*MM,152*MM),colorspace=pymupdf.csGRAY)
        return np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width).astype(float)/255
    a=copper(paths[0]);b=copper(paths[1])[:,::-1]
    mirror_error=float(np.abs(a-b).mean());assert mirror_error<.02,mirror_error
    with (ROOT/'jumpers.csv').open() as f:assert len(list(csv.DictReader(f)))==len(board['jumpers'])
    for target in re.findall(r'\]\(([^)]+)\)',(ROOT.parent/'wiring.md').read_text()):
        if not target.startswith(('http:','https:','#')):assert (ROOT.parent/target).exists(),target
    report=dict(revision=board['revision'],pdf_count=len(paths),pages=pages,
                page_size='PDF 01-03: A4; PDF 04: A3 landscape',calibration_line_mm=found[0],
                transfer_vs_bottom_mirror_pixel_mean_error=mirror_error,jumper_count=len(board['jumpers']),
                component_count=len(board['components']),relative_wiring_links='all exist',
                status='digital print checks passed; physical prototype and direct3.3V HC TRIG untested')
    (ROOT/'print-check.json').write_text(json.dumps(report,indent=2)+'\n')
    files=['design.py','route_board.py','validate_board.py','export_board.py','export_component_map.py','draw_system.py','check_release.py','board.json','pinmap.json','bom.csv','jumpers.csv','pads.csv','drc-report.json','print-check.json','component-map-check.json']
    files += [str(p.relative_to(ROOT)) for p in paths]
    files += [str(p.relative_to(ROOT)) for p in sorted((ROOT/'output/svg').glob('*.svg'))]
    release=dict(revision=board['revision'],controller='Raspberry Pi Zero, no Nano',
        motor_driver='two DRV8825 carriers, Pololu2133 pinout',
        manufacturing=f'single-sided home etch; {len(board["jumpers"])} insulated jumpers required',
        board_mm=[board['width'],board['height']],ws2812_present=False,buffer_ic_present=False,
        hc_trig='direct Pi GPIO17 3.3V; R9 100k pull-down; verify actual HC-SR04 module',
        hc_echo='R2 2k2 / R3 2k7 divider retained',physical_prototype_tested=False,
        firmware_stepper_implemented=False,digital_drc_passed=True,
        sha256={f:digest(ROOT/f) for f in files})
    (ROOT/'release.json').write_text(json.dumps(release,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
