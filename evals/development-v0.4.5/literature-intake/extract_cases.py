#!/usr/bin/env python3
"""Extract exact stored numeric strings; no inference of pairing or model results."""
from __future__ import annotations
import csv
import hashlib
import json
import math
from pathlib import Path
from collections import Counter, defaultdict
from statistics import mean, stdev
from xml.etree import ElementTree as ET
from zipfile import ZipFile

BASE = Path(__file__).resolve().parent
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
REL_NS = '{http://schemas.openxmlformats.org/package/2006/relationships}'


def sheets(path):
    with ZipFile(path) as z:
        shared = []
        if 'xl/sharedStrings.xml' in z.namelist():
            for item in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si', NS):
                shared.append(''.join(node.text or '' for node in item.iter('{'+NS['m']+'}t')))
        rel = {x.attrib['Id']: x.attrib['Target'] for x in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        result = {}
        for s in ET.fromstring(z.read('xl/workbook.xml')).findall('m:sheets/m:sheet', NS):
            target = rel[s.attrib['{'+NS['r']+'}id']]
            target = target.lstrip('/') if target.startswith('/') else 'xl/'+target
            cells = {}
            for c in ET.fromstring(z.read(target)).findall('.//m:c', NS):
                t = c.attrib.get('t', 'n'); v = c.find('m:v', NS)
                if t == 'inlineStr': value = ''.join(n.text or '' for n in c.findall('.//m:t', NS))
                elif v is None: continue
                elif t == 's': value = shared[int(v.text)]
                else: value = v.text
                cells[c.attrib['r']] = {'value': value, 'type': t}
            result[s.attrib['name']] = cells
        return result


def numeric(cells, cell):
    val = cells.get(cell)
    if val is None: return None
    assert val['type'] == 'n', (cell, val)
    number = float(val['value']); assert math.isfinite(number)
    return val['value']


def text(cells, cell, expected):
    assert cells[cell]['value'] == expected, (cell, cells.get(cell), expected)


def write_csv(path, records, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fields); w.writeheader(); w.writerows(records)


def save_contract(name, obj):
    (BASE/name/'input-contract.json').write_text(json.dumps(obj, indent=2)+'\n')


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def scwat_expression():
    name = 'scwat-expression'; file = BASE/'41467_2023_43021_MOESM8_ESM.xlsx'; cells = sheets(file)['Fig. 2b']
    text(cells, 'A1', 'thermogenesis term gene'); text(cells, 'B1', 'TPM')
    aliases = {'F1': 'YT-FF', 'F2': 'YT-FF', 'F3': 'YT-FF', 'A1': 'YT-AKO', 'A2': 'YT-AKO', 'A3': 'YT-AKO'}
    records=[]; genes=[]
    for row in range(3,32):
        gene=cells[f'A{row}']['value']; genes.append(gene)
        for col in 'BCDEFG':
            sample = cells[f'{col}2']['value']; assert sample in aliases
            value = numeric(cells, f'{col}{row}'); assert value is not None and float(value) >= 0
            records.append({'gene': gene, 'sample': sample, 'condition': aliases[sample], 'tpm': value, 'source_sheet': 'Fig. 2b', 'source_cell': f'{col}{row}', 'source_gene_cell': f'A{row}', 'source_sample_cell': f'{col}2'})
    assert len(records)==174 and len(set(genes))==29
    write_csv(BASE/name/'observations.csv',records,list(records[0]))
    save_contract(name, {'track':'create','source_file':file.name,'source_sha256':sha(file),'article':'https://www.nature.com/articles/s41467-023-43021-8','doi':'10.1038/s41467-023-43021-8','license':'CC BY 4.0','source_sheet':'Fig. 2b','question':'Which thermogenic genes have a consistent genotype-associated expression difference across the six supplied mouse samples, and which vary among samples?','experimental_unit':'mouse; 3 mice per genotype, as specified in the Fig. 2 caption','pairing':'unpaired; F1 and A1 do not establish paired mice','observations':174,'genes':genes,'samples':['F1','F2','F3','A1','A2','A3'],'condition_aliases':aliases,'alias_evidence':'Source F/A sample headers matched to explicit Fig. 2b labels YT-FF1–3 / YT-AKO1–3, not inferred from numerical patterns.','unit':'TPM; already author-produced RNA-seq abundance','allowed_display_transform':'log2(TPM + 1), pseudocount 1 TPM, if clearly adopted and documented; no additional upstream normalization','allowed_descriptive_contrast':'difference of genotype means of log2(TPM + 1), computed from the three sample values in each group; label as descriptive log-expression difference, not DESeq2 fold change','zero':'Atp5o has six explicit numeric zeros; author marks not detectable. Retain as observed zero / below detection, not missing.','missing':0,'source_statistics':'Source does not supply plotted row-z scores, linkage or per-gene adjusted P values. Do not reconstruct original stars or dendrogram; no new statistical significance layer is required.','retain':'all 174 source values, all 29 genes and all six samples; full source cell trace','suggested_design':'sample-level expression heatmap with genotype band, gene labels, absolute log-expression colorbar and a separate descriptive mean-contrast lane using shared row alignment','literature_reference':'../scwat-figure2b-reference.png','reference_role':'learn legible gene rows, contiguous sample groups, thin cell boundaries and small guide footprint; original z-score colors and dendrogram are not a reproduction target'})
    return len(records)


def vanneste_ccl2():
    name='vanneste-ccl2'; file=BASE/'41590_2023_1468_MOESM5_ESM.xlsx'; cells=sheets(file)['3c']
    text(cells,'A1','Lung Ccl2'); text(cells,'M1','Serum Ccl2'); text(cells,'A2','Hours post-DT'); text(cells,'M2','Hours post-DT')
    blocks=[('Lung','pg mg−1 protein','A', 'Control','BCDEF'),('Lung','pg mg−1 protein','A','IM-DTR','GHIJKL'),('Serum','pg ml−1','M','Control','NOPQRSTU'),('Serum','pg ml−1','M','IM-DTR',['V','W','X','Y','Z','AA','AB','AC'])]
    text(cells,'B2','Control'); text(cells,'G2','IM-DTR'); text(cells,'N2','Control'); text(cells,'V2','IM-DTR')
    records=[]; absent=[]
    for compartment, unit,timecol,condition,cols in blocks:
        for row in range(3,7):
            hour=numeric(cells,f'{timecol}{row}'); assert hour in ['0','12','24','48']
            for col in cols:
                cell=f'{col}{row}'; value=numeric(cells,cell)
                if value is None:
                    absent.append({'compartment':compartment,'condition':condition,'hour':hour,'source_cell':cell}); continue
                assert float(value)>=0
                records.append({'compartment':compartment,'condition':condition,'hour':hour,'ccl2':value,'unit':unit,'source_sheet':'3c','source_cell':cell,'source_time_cell':f'{timecol}{row}'})
    write_csv(BASE/name/'observations.csv',records,list(records[0])); write_csv(BASE/name/'blank-cells.csv',absent,list(absent[0]))
    p=[]
    for compartment,rowstart,timecol,pcol in [('Lung',9,'B','C'),('Serum',10,'N','O')]:
        for row in range(rowstart,rowstart+4):
            p.append({'compartment':compartment,'hour':numeric(cells,f'{timecol}{row}'),'adjusted_p':cells[f'{pcol}{row}']['value'],'source_sheet':'3c','source_cell':f'{pcol}{row}','comparison':'Control vs IM-DTR'})
    write_csv(BASE/name/'author-adjusted-p.csv',p,list(p[0]))
    groups=defaultdict(list)
    for r in records:groups[(r['compartment'],r['condition'],r['hour'])].append(float(r['ccl2']))
    summary=[]
    for key, values in groups.items():
        summary.append(dict(zip(['compartment','condition','hour'],key),n=len(values),mean=mean(values),sem=stdev(values)/math.sqrt(len(values))))
    write_csv(BASE/name/'descriptive-summary.csv',summary,list(summary[0]))
    save_contract(name,{'track':'create','source_file':file.name,'source_sha256':sha(file),'article':'https://www.nature.com/articles/s41590-023-01468-3','doi':'10.1038/s41590-023-01468-3','license':'CC BY 4.0','source_sheet':'3c','question':'When does Ccl2 rise after DT in lung and serum, and how do the IM-DTR and control groups differ across the four measured hours?','experimental_unit':'mouse; Methods MCP-1/Ccl2 quantification explicitly states euthanasia at indicated times, followed by blood collection and lung dissection; terminal cross-sectional time groups, pooled from two experiments in the caption','design_evidence':'Official Methods MCP-1/Ccl2 quantification; user-provided PDF page 16. Blood and lung were collected after euthanasia. Some cross-compartment samples may derive from the same mice, but no IDs connect supplied entries and compartment group counts differ.','conditions':['Control','IM-DTR'],'hours':[0,12,24,48],'unit_by_compartment':{'Lung':'pg mg−1 protein','Serum':'pg ml−1'},'observations':len(records),'blank_source_cells':len(absent),'group_counts':[{k:v for k,v in r.items() if k in ['compartment','condition','hour','n']} for r in summary],'pairing':'No mouse ID or experimental-batch ID supplied; source column positions do not authorize pairing across time, compartment or genotype. Do not connect individual animals.','summary':'mean ± SEM; sample standard deviation with ddof=1 divided by sqrt(n), matching the adopted descriptive summary definition','statistics':'8 author-supplied adjusted P values, including threshold strings <0.0001; preserve as source results of two-way ANOVA / Tukey from the caption. Scope of the correction family across compartments is not explicitly stated. Do not claim compartment-specific or global adjustment, reconstruct experiment IDs, or present independent recalculation','missing':'blank numeric cells are unavailable entries, not zero and not omitted observations; n is the actual nonblank count','retain':'all observations and source-cell traces; summaries use every supplied value','time_conflict':'Publication panel xlabel says Days post-DT, but workbook header and caption explicitly specify 0,12,24,48 hours. The Create panel uses Hours post-DT and documents correction instead of copying that error.','suggested_design':'two aligned compartment lanes with common linear time positions 0/12/24/48 h, independent labeled numeric axes/units, raw points offset only physically within time, compact mean/SEM summaries or straight mean trajectories, clearly decoded genotype and separately placed significance annotations','literature_reference':'../vanneste-figure3c-reference.png','reference_role':'learn compact grouped observations + mean/SEM hierarchy and explicit independent compartment axes; do not copy the erroneous days label or force a reproduction of the bar layout'})
    return len(records)


def progeny():
    name='progeny-signatures'; file=BASE/'41467_2017_2391_MOESM4_ESM.xlsx'; cells=sheets(file)['Sheet1']; pathways=[cells[f'{col}2']['value']for col in 'BCDEFGHIJKL']; records=[]
    for row in range(3,1016):
        gene=cells[f'A{row}']['value']
        for col,pathway in zip('BCDEFGHIJKL',pathways):
            value=numeric(cells,f'{col}{row}'); assert value is not None
            records.append({'gene':gene,'pathway':pathway,'coefficient':value,'source_sheet':'Sheet1','source_cell':f'{col}{row}'})
    write_csv(BASE/name/'coefficients.csv',records,list(records[0])); bypath=defaultdict(dict)
    for r in records:bypath[r['pathway']][r['gene']]=float(r['coefficient'])
    overlap=[]
    for a in pathways:
        for b in pathways:
            common=[g for g in bypath[a] if bypath[a][g]!=0 and bypath[b][g]!=0]
            concordant=sum(bypath[a][g]*bypath[b][g]>0 for g in common)
            union=sum(bypath[a][g]!=0 or bypath[b][g]!=0 for g in bypath[a])
            overlap.append({'pathway_a':a,'pathway_b':b,'shared_nonzero_genes':len(common),'nonzero_union_genes':union,'jaccard':len(common)/union,'concordant_nonzero_genes':concordant,'sign_agreement':concordant/len(common) if common else '', 'source_genes':';'.join(common)})
    write_csv(BASE/name/'derived-overlap.csv',overlap,list(overlap[0]))
    save_contract(name,{'track':'create','intended_version':'0.4.6','source_file':file.name,'source_sha256':sha(file),'article':'https://www.nature.com/articles/s41467-017-02391-6','doi':'10.1038/s41467-017-02391-6','license':'CC BY 4.0','question':'Which PROGENy pathway signatures share response genes, and are their shared coefficients aligned or opposed in sign?','unit':'published linear-model coefficient; not expression, pathway activity, or experimentally confirmed cross-talk','genes':1013,'pathways':pathways,'observations':len(records),'nonzero_coefficients':1100,'nonzero_per_pathway':100,'shared_genes':87,'unique_pathway_genes':926,'shared_gene_degree':2,'pairing':'model coefficients, not biological observations or paired experiments','zero':'Every gene/pathway coordinate is supplied. Numeric zero is a structural unselected coefficient, not an unmeasured cell.','overlap_definition':'A gene is shared when both published coefficients are nonzero. Diagonal = 100. Shared/union is Jaccard; each pathway denominator is 100, so shared/100 is fraction of either signature.','sign_agreement_definition':'Number of shared genes with product of coefficients > 0 divided by shared count; undefined and blank when shared count is zero, never filled with zero agreement.','statistics':'descriptive derived counts and ratios; no inferential P value or pathway-score calculation','suggested_design':'annotated lower-triangle shared-count matrix with separately decoded shared-weight sign agreement; no arbitrary gene selection or upstream model fitting','retain':'all 11,143 exact coefficient cells; derived pair records list exact contributing genes','literature_reference':'../progeny-figure2-reference.png','reference_role':'learn distinct magnitude/sign encoding and sparse readable matrix organization; Figure 2 association statistics are a different scientific quantity and not the plotting target'})
    return len(records)


def conflict_case():
    file=BASE/'41590_2023_1468_MOESM5_ESM.xlsx'; cells=sheets(file)['3b']; p={}
    for labelrow in [1,14,27,40,53,66]:
        text(cells,f'B{labelrow+1}','- DT'); text(cells,f'L{labelrow+1}','+ DT')
        p[cells[f'A{labelrow}']['value']]=numeric(cells,f'B{labelrow+10}')
    (BASE/'vanneste-figure3b-excluded.json').write_text(json.dumps({'status':'excluded_pending_group_identity_resolution','source_sheet':'3b','source_header_groups':['- DT','+ DT'],'caption_legend_groups':['Control','IMDTR'],'reason':'Time-course article legend/caption describes littermate controls vs IMDTR, while workbook headers use treatment labels. No supplied machine-readable key resolves that difference. Retain the raw workbook and reference crop; do not silently relabel groups or infer identical animals across columns.','author_model_p':p},indent=2)+'\n')

if __name__ == '__main__':
    print('scWAT expression',scwat_expression())
    print('Vanneste Ccl2',vanneste_ccl2())
    print('PROGENy',progeny())
    conflict_case()
