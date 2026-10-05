#!/usr/bin/env python3
"""Place original/baseline/revised PDFs at actual size; never normalize panels."""
from pathlib import Path
import json
import pymupdf

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PT = 72 / 25.4
RADAR_SOURCE = Path('/Users/starry/Desktop/Res/Post-MI/ref/singlecell RNA-seq/Massier. et al., NC, 2023/Massier. et al., NC, 2023.pdf')


def place(page, path, x_mm, y_mm, width_mm=None, height_mm=None, page_index=0, clip=None):
    with pymupdf.open(path) as document:
        source = document[page_index]
        region = pymupdf.Rect(clip) if clip else source.rect
        width_mm = region.width / PT if width_mm is None else width_mm
        height_mm = region.height / PT if height_mm is None else height_mm
        target = pymupdf.Rect(x_mm * PT, y_mm * PT, (x_mm + width_mm) * PT, (y_mm + height_mm) * PT)
        page.show_pdf_page(target, document, page_index, clip=region)
        return {'path': str(path), 'source_page': page_index + 1, 'clip_points': list(region),
                'placed_mm': [x_mm, y_mm, width_mm, height_mm], 'physical_scale': 'actual PDF points retained'}


def label(page, x, y, value):
    page.insert_text((x * PT, y * PT), value, fontsize=9, fontname='helv')


def main():
    document = pymupdf.open()
    entries = []
    forest = ROOT / 'examples/no-author-code/vabistsevits-forest'
    page = document.new_page(width=430 * PT, height=172 * PT)
    for x, title in [(5, 'Original Figure 3a,b'), (101, 'Prior total-effect panel'), (213, 'Prior direct-effect panel'), (325, 'Revised paired lanes')]:
        label(page, x, 8, title)
    entries.append(place(page, HERE / 'sources/s41467-024-48105-7.pdf', 5, 15, page_index=4, clip=[42, 44, 294, 440]))
    entries.append(place(page, HERE / 'baseline/vabistsevits-forest/output-a/panel.pdf', 101, 15))
    entries.append(place(page, HERE / 'baseline/vabistsevits-forest/output-b/panel.pdf', 213, 15))
    entries.append(place(page, forest / 'revision-v0.4.6/output/panel.pdf', 325, 15))
    label(page, 5, 167, 'Actual-size comparison. Vabistsevits et al., Nature Communications (2024), DOI 10.1038/s41467-024-48105-7, CC BY 4.0. Crop/layout adaptations are declared separately.')

    radar = ROOT / 'examples/no-author-code/massier-integration-radar'
    page = document.new_page(width=348 * PT, height=122 * PT)
    for x, title in [(5, 'Original Figure 1e: selected depot kBET is the central left radar'), (181, 'Prior 88 x 88 mm'), (274, 'Revised 64 x 66 mm')]:
        label(page, x, 8, title)
    entries.append(place(page, RADAR_SOURCE, 5, 15, page_index=2, clip=[68, 492, 537, 663]))
    entries.append(place(page, HERE / 'baseline/massier-integration-radar/panel.pdf', 181, 15))
    entries.append(place(page, radar / 'revision-v0.4.6/output/panel.pdf', 274, 15))
    label(page, 5, 111, 'Actual circle diameters: source selected radar 23.88 mm; prior 50 mm; revised 34 mm. Points: source ~3.575 pt; prior 3.8 pt; revised 5.1 pt. Standalone class labels are adapted.')
    label(page, 5, 118, 'Massier et al., Nature Communications (2023), DOI 10.1038/s41467-023-36983-2, CC BY 4.0. No source values or radial semantics are inferred from pixels.')

    page = document.new_page(width=284 * PT, height=118 * PT)
    label(page, 5, 8, 'Original Shi Figure 1d')
    label(page, 85, 8, 'Current 100 x 76 mm: measured control, no revision')
    entries.append(place(page, HERE / 'sources/s41467-021-22092-5.pdf', 5, 15, page_index=2, clip=[294, 188, 473, 323]))
    entries.append(place(page, HERE / 'baseline/shi-timecourse/output/panel.pdf', 85, 15))
    label(page, 196, 21, 'Original type (PDF metadata):')
    label(page, 196, 27, 'Axis 10.693 pt; ticks 8.911 pt')
    label(page, 196, 33, 'Axis/tick ratio ~1.20')
    label(page, 196, 42, 'Current: uniform 8 pt Arial')
    label(page, 196, 48, 'Potential hierarchy change')
    label(page, 196, 54, 'must be explicitly adopted.')
    label(page, 5, 110, 'Shi et al., Nature Communications (2021), DOI 10.1038/s41467-021-22092-5, CC BY 4.0. Physical source crop and current panel are shown at their actual sizes.')
    path = HERE / 'physical-scale-comparison.pdf'
    document.save(path, garbage=4, deflate=True)
    for index, page in enumerate(document):
        page.get_pixmap(matrix=pymupdf.Matrix(96 / 72, 96 / 72)).save(HERE / f'physical-scale-comparison-{index + 1}.png')
    document.close()
    (HERE / 'physical-scale-placement.json').write_text(json.dumps({'scope': 'Review sheet only; manuscript panels themselves contain no added narrative.', 'placements': entries}, indent=2) + '\n')
    print(path)


if __name__ == '__main__':
    main()
