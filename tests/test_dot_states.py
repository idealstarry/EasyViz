"""Distinguish data availability from zero without inflating quantitative dots."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd
from marker_geometry import collection_fill_areas_pt2

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/easyviz/scripts/render.py'
loader = importlib.util.spec_from_file_location('easyviz_dot_states_test', SCRIPT)
renderer = importlib.util.module_from_spec(loader)
loader.loader.exec_module(renderer)


class DotStateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='easyviz-states-')
        self.root = Path(self.temporary.name)
        self.input = self.root / 'data.csv'
        self.body = 'x,y,size,color,state\nA,F1,100,1,observed\nB,F1,0,0,observed\nC,F1,.001,.001,observed\nD,F1,,,unmeasured\nA,F2,20,.2,observed\n'
        self.input.write_text(self.body)
        self.spec = {'chart':'dotplot', 'fields':{'x':'x','y':'y','size':'size','color':'color','state':'state'},
                     'layout':{'width_mm':180,'height_mm':125,'font':'DejaVu Sans','dpi':120,
                               'margins':{'left':.12,'right':.65,'bottom':.18,'top':.9}},
                     'options':{'size_max':100,'max_area_pt2':90,'color_limits':[0,1],'small_positive_area_pt2':1},
                     'formats':['svg','png']}

    def tearDown(self):
        renderer.plt.close('all')
        self.temporary.cleanup()

    def test_states_preserve_numeric_dot_area_and_source_rows(self):
        renderer.render(self.input,self.spec,self.root / 'output')
        qa=json.loads((self.root/'output/qa.json').read_text())
        state=qa['dot_states']
        self.assertEqual(state['observed_rows'],4)
        self.assertEqual(state['zero_rows'],1)
        self.assertEqual(state['unmeasured_rows'],1)
        self.assertEqual(len(state['missing_coordinates']),3)
        self.assertEqual(state['small_positive_rows'],1)
        self.assertEqual(state['symbols'],{'Measured zero':'_','Not measured':'x','Not supplied':'+','Small positive':'|'})
        plotted=pd.read_csv(self.root/'output/plotting-data.csv',keep_default_na=False)
        self.assertEqual(len(plotted),5)
        self.assertEqual(plotted.loc[3,'_easyviz_area_pt2'],'')
        np.testing.assert_allclose(pd.to_numeric(plotted.loc[[0,1,2,4],'_easyviz_area_pt2']),[90,0,.0009,18])
        np.testing.assert_allclose(pd.to_numeric(plotted.loc[[0,1,2,4],'_easyviz_marker_size_parameter_pt2']),np.array([90,0,.0009,18])*4/np.pi)
        self.assertEqual(self.input.read_text(),self.body)
        data=renderer.prepare(self.input,self.spec)
        layout,typography,rc=renderer.setup(self.spec)
        with renderer.plt.rc_context(rc):
            fig,_=renderer.draw(data,self.spec,layout,typography,{'method':'none'})
            np.testing.assert_allclose(collection_fill_areas_pt2(fig.axes[0].collections[0],fig),[90,0,.0009,18],rtol=1e-6,atol=1e-12)
            keys=next(entry for entry in fig._easyviz_legend_layout.entries if entry['kind']=='size')
            np.testing.assert_allclose([collection_fill_areas_pt2(handle,fig)[0] for handle in keys['artist'].legend_handles],[22.5,45,90],rtol=1e-6)
            self.assertEqual(len(fig.axes[0].collections[0].get_offsets()),4)
            self.assertEqual(len(fig.axes[0].collections),5)

    def test_unmeasured_does_not_accept_zero_or_nan_as_supplied_measurement(self):
        for replacement in ('D,F1,0,0,unmeasured','D,F1,NaN,,unmeasured','D,F1,,,observed','D,F1,,,missing'):
            with self.subTest(row=replacement):
                self.input.write_text(self.body.replace('D,F1,,,unmeasured',replacement))
                with self.assertRaises(renderer.SpecError):renderer.prepare(self.input,self.spec)

    def test_absent_coordinates_require_declared_meaning_when_strict(self):
        spec=deepcopy(self.spec)
        spec['options']['missing_cells']='error'
        with self.assertRaisesRegex(renderer.SpecError,'Missing dot coordinates'):
            renderer.render(self.input,spec,self.root/'strict')
        spec['options']['missing_cells']='unmeasured'
        renderer.render(self.input,spec,self.root/'declared')
        state=json.loads((self.root/'declared/qa.json').read_text())['dot_states']
        self.assertEqual(state['missing_cells_meaning'],'unmeasured')
        self.assertNotIn('Not supplied',state['symbols'])

    def test_state_only_matrix_does_not_invent_numeric_values_or_scales(self):
        self.input.write_text('x,y,size,color,state\nA,F1,,,unmeasured\nB,F1,,,unmeasured\n')
        renderer.render(self.input,self.spec,self.root/'unmeasured')
        qa=json.loads((self.root/'unmeasured/qa.json').read_text())
        self.assertEqual(qa['dot_states']['observed_rows'],0)
        self.assertEqual(qa['dot_states']['symbols'],{'Not measured':'x'})
        self.assertEqual([x['kind'] for x in qa['legend_layout']['legends']],['categorical'])


if __name__=='__main__':unittest.main()
