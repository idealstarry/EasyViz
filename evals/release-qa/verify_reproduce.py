"""Independently verify the held-out reproduction from source and SVG geometry."""
from pathlib import Path
import hashlib,json,re
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap,to_hex
ROOT=Path(__file__).resolve().parent
folder=ROOT/'forward-reproduce'
source=pd.read_csv(ROOT/'inputs/reproduce/source.csv')
plotted=pd.read_csv(folder/'plotting-data.csv')
keys=['population','marker']; fields=['detected_fraction','mean_scaled_expression']
original=source.set_index(keys); displayed=plotted.set_index(keys)
assert len(original)==61 and original.index.is_unique and displayed.index.is_unique
for field in fields:
 np.testing.assert_allclose(displayed.loc[original.index,field],original[field],rtol=0,atol=1e-12)
missing=set(displayed.index)-set(original.index)
assert len(displayed)==64 and len(missing)==3
assert displayed.loc[list(missing),fields].isna().all().all()
assert set(displayed.index[displayed.state=='measured_zero'])==set(original.index[original.detected_fraction==0])
svg=ET.parse(folder/'panel.svg').getroot(); ns={'s':'http://www.w3.org/2000/svg'}
def circle(p):
 values=np.array([float(v) for v in re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',p.attrib['d'])]).reshape(-1,2)
 lo,hi=values.min(0),values.max(0)
 np.testing.assert_allclose(hi[0]-lo[0],hi[1]-lo[1],atol=2e-6)
 return (lo+hi)/2,(hi[0]-lo[0])**2
main=svg.find(".//s:g[@id='PathCollection_1']",ns)
paths=main.findall('s:path',ns)
geometry=[circle(p) for p in paths]
xs=sorted(set(round(c[0],4) for c,a in geometry));ys=sorted(set(round(c[1],4) for c,a in geometry))
assert len(xs)==len(ys)==8 and len(paths)==59
populations=list(dict.fromkeys(source.population));markers=list(dict.fromkeys(source.marker))
cmap=LinearSegmentedColormap.from_list('independent',['#2581b9','#f7f8f9','#cc86b9'])
seen=set();errors=[]
for p,(center,area) in zip(paths,geometry):
 key=(populations[ys.index(round(center[1],4))],markers[xs.index(round(center[0],4))])
 r=original.loc[key]; assert r.detected_fraction>0 and key not in seen;seen.add(key)
 errors.append(abs(area-64*r.detected_fraction))
 assert errors[-1]<2e-5
 color=re.search(r'fill:\s*(#[0-9a-fA-F]{6})',p.attrib['style']).group(1).lower()
 assert color==to_hex(cmap((r.mean_scaled_expression+2)/4)),(key,color)
assert seen==set(original.index[original.detected_fraction>0])
missing_group=svg.find(".//s:g[@id='PathCollection_2']",ns)
actual_missing=set()
for mark in missing_group.findall('.//s:use',ns):
 center=[float(mark.get('x')),float(mark.get('y'))]
 actual_missing.add((populations[ys.index(round(center[1],4))],markers[xs.index(round(center[0],4))]))
assert actual_missing==missing
for group_id,fraction in zip([4,5,6],[.25,.5,1]):
 p=svg.find(f".//s:g[@id='PathCollection_{group_id}']/s:path",ns)
 assert abs(circle(p)[1]-fraction*64)<2e-5
report={'status':'pass','source_rows':len(source),'display_coordinates':len(displayed),'svg_positive_circles':len(paths),'svg_missing_crosses':len(actual_missing),'measured_zeros':2,'source_value_max_tolerance':1e-12,'max_svg_scatter_area_error_pt2':max(errors),'colors':'All 59 fills match each source expression value under the declared linear scale and color stops.','size_keys':'All three SVG key circles use the same 64 × fraction scatter area mapping.','hashes':{f:hashlib.sha256((folder/f).read_bytes()).hexdigest() for f in ['panel.svg','plotting-data.csv']},'scope':'Independent root check of original source, plotting table and actual SVG mark geometry. No implementation or implementer verification code was read. This checks the adopted palette mapping, not exact original-reference colors or print visibility.'}
(ROOT/'reproduce-numeric-review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
