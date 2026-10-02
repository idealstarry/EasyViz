#!/usr/bin/env python3
"""Prepare already-published source scores; never rerun deconvolution."""
from pathlib import Path
import argparse, hashlib, json
import pandas as pd

HERE = Path(__file__).resolve().parent

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('workbook', type=Path)
    args=ap.parse_args()
    annotations=json.loads((HERE/'annotations.json').read_text())
    rows=[]
    for cohort,sheet,subject,time,lookup in [
        ('Petrus','Petrus, P. et al','ID','Timepoint',{'Före':0,'Efter':2}),
        ('Kerr','Kerr, A. et al.','subject','time_point',{'B':0,'C':2,'D':5}),
    ]:
        frame=pd.read_excel(args.workbook,sheet)
        for i,row in frame.iterrows():
            for annotation in annotations:
                column=f'Myeloid_{annotation["cluster"]}'
                rows.append(dict(cohort=cohort,participant=str(row[subject]),year=lookup[row[time]],
                                 subtype=f'myC{annotation["cluster"]:02}',score=float(row[column]),
                                 source_sheet=sheet,source_excel_row=int(i+2),source_column=column))
    data=pd.DataFrame(rows)
    data.to_csv(HERE/'source-data.csv',index=False,float_format='%.17g')
    print(json.dumps({'rows':len(data),'source_sha256':hashlib.sha256(args.workbook.read_bytes()).hexdigest(),
                      'prepared_sha256':hashlib.sha256((HERE/'source-data.csv').read_bytes()).hexdigest()},indent=2))

if __name__=='__main__': main()
