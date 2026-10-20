"""Test Streamlit-independent UI model and schematic functions by AST extraction.
Streamlit itself is tested on deployment once dependencies are installed.
"""
import ast
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from solver import Config, Stage, validate, solve

APP=Path(__file__).resolve().parents[1]/'app.py'
source=ast.parse(APP.read_text(encoding='utf-8'))
functions={n.name:n for n in source.body if isinstance(n,ast.FunctionDef)}

class State(dict):
    def __getattr__(self,key): return self[key]
    def __setattr__(self,key,value): self[key]=value
    def setdefault(self,*args): return super().setdefault(*args)


def ui():
    code=compile(ast.Module(body=[functions[name] for name in ('setup_state','resize_stages','configuration','import_system','system_svg')],type_ignores=[]),str(APP),'exec')
    s=State()
    ns={'st':SimpleNamespace(session_state=s),'Config':Config,'Stage':Stage,
        'FIELDS':tuple(asdict(Config())), 'STAGE_FIELDS':tuple(asdict(Stage())),
        'asdict':asdict,'validate':validate,'DUSK':'#181618','STARDUST':'#9100FF',
        'MOON':'#FFFFFF','GOLD':'#DBC885'}
    exec(code,ns)
    return ns,s


def test_new_stages_have_correct_defaults_and_preserve_hidden_values():
    u,s=ui();u['setup_state']()
    s.stage_count=9;u['resize_stages']()
    assert s['stage_8_cd']==Stage().cd
    s['stage_8_pipe_l_m']=3.14
    s.stage_count=1;u['resize_stages']()
    s.stage_count=9;u['resize_stages']()
    assert s['stage_8_pipe_l_m']==3.14


def test_config_fields_remain_stable_across_reruns():
    u,s=ui();u['setup_state']()
    s['cfg_gas_constant']=293.0
    u['setup_state']()
    assert u['configuration']()[0].gas_constant==293.0


def test_import_replaces_existing_widget_keys():
    u,s=ui();u['setup_state']()
    c=asdict(Config());c['gamma']=1.32
    stages=[asdict(Stage()) for _ in range(4)]
    stages[2]['cd']=.71
    u['import_system']({'config':c,'stages':stages})
    assert s.stage_count==4 and s['cfg_gamma']==1.32
    assert s['stage_2_cd']==.71
    assert len(u['configuration']()[1])==4


def test_schematic_resizes_and_reports_matching_dimensions():
    u,s=ui();u['setup_state']()
    for n in (1,2,3,6,12):
        ss=[Stage(pipe_l_m=.25+i*.1,orifice_d_mm=5+i) for i in range(n)]
        svg=u['system_svg'](ss)
        assert svg.startswith('<svg ') and svg.endswith('</svg>')
        assert svg.count('<rect x=')==1+2*n
        assert svg.count('Pipe Ø')==n
        assert f'O{n:02}' in svg


def test_a_range_of_stage_counts_and_both_fluids():
    for fluid in ('Gas','Liquid'):
        for n in (1,2,3,6,12):
            c=Config(fluid=fluid)
            stages=[Stage() for _ in range(n)]
            validate(c,stages)
            result=solve(c,stages)
            assert result['mass_flow_kg_s']>=0
            assert len(result['stages'])==n
