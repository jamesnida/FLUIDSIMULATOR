import pytest
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
from units import *

APP=Path(__file__).resolve().parents[1]/'app.py'
source=ast.parse(APP.read_text(encoding='utf-8'))
functions={n.name:n for n in source.body if isinstance(n,ast.FunctionDef)}

class State(dict):
    def __getattr__(self,key): return self[key]
    def __setattr__(self,key,value): self[key]=value
    def setdefault(self,*args): return super().setdefault(*args)


def ui():
    code=compile(ast.Module(body=[functions[name] for name in ('setup_state','resize_stages','configuration','import_system','system_svg','change_units')],type_ignores=[]),str(APP),'exec')
    s=State()
    ns={'st':SimpleNamespace(session_state=s),'Config':Config,'Stage':Stage,
        'FIELDS':tuple(asdict(Config())), 'STAGE_FIELDS':tuple(asdict(Stage())),
        'asdict':asdict,'validate':validate,'DUSK':'#181618','STARDUST':'#9100FF',
        'MOON':'#FFFFFF','GOLD':'#DBC885', 'convert_config':convert_config,
        'convert_stage':convert_stage,'read_config':read_config,'read_stage':read_stage,
        'to_display':to_display,'to_canonical':to_canonical, 'CONFIG_KINDS':CONFIG_KINDS,
        'STAGE_KINDS':STAGE_KINDS,'unit':unit}
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


def test_unit_switch_preserves_physics_and_edits():
    u,s=ui();u['setup_state']()
    before=u['configuration']()
    s['_previous_unit_system']='SI'
    s['unit_system']='US customary'
    u['change_units']()
    after=u['configuration']()
    assert after[0].inlet_psia==pytest.approx(before[0].inlet_psia)
    assert after[0].temperature_k==pytest.approx(before[0].temperature_k)
    assert after[1][0].pipe_l_m==pytest.approx(before[1][0].pipe_l_m)
    assert s['stage_0_orifice_d_mm']==pytest.approx(.5)
    s['stage_0_pipe_l_m']=3280.839895013123
    assert u['configuration']()[1][0].pipe_l_m==pytest.approx(1000.)
    s['unit_system']='SI';u['change_units']()
    assert s['stage_0_pipe_l_m']==pytest.approx(1000.)


def test_display_table_has_units_and_dimensionless_metrics():
    r=solve(Config(),[Stage()])
    for sys in SYSTEMS:
        label=labeled_rows(r['stages'],'Gas',sys)[0]
        assert any(k.startswith('Inlet static pressure (') for k in label)
        assert 'Fanno utilization (%)' in label
        assert 'Pipe sonic (Mach 1)' in label


def test_units_roundtrip_every_dimension():
    for kind in UNITS['SI']:
        for v in (0.2,2.3,102.4):
            back=to_canonical(to_display(v,kind,'US customary'),kind,'US customary')
            assert back==pytest.approx(v,rel=1e-9,abs=1e-9)


def test_incompressible_display_has_units():
    r=solve(Config(fluid='Liquid'),[Stage()])
    data=labeled_rows(r['stages'],'Liquid','US customary')[0]
    assert 'Pipe ΔP (psi)' in data
    assert 'Cavitation onset screening' in data


def selection_helpers():
    names=['results_columns','selected_results','update_results_selection']
    code=compile(ast.Module(body=[functions[name] for name in names],type_ignores=[]),str(APP),'exec')
    state=State()
    ns={'unit':unit,'RESULT_FIELDS':{
     'all':(('stage','Stage',True),('inlet','Inlet static pressure',True),('outlet','Outlet static pressure',True),('orifice_dp','Orifice pressure drop',True),('pipe_dp','Pipe pressure drop',True),('re','Reynolds number',False),('friction','Darcy friction factor',False)),
     'Gas':(('mach_in','Pipe inlet Mach',True),('mach_out','Pipe outlet Mach',True),('capacity','Fanno capacity',False),('consumed','Fanno consumed',False),('remaining','Fanno remaining',False),('utilization','Fanno utilization',True),('pipe_sonic','Pipe sonic',True),('orifice_sonic','Orifice sonic candidate',True)),
     'Liquid':(('cavitation_limit','Orifice cavitation limit',True),('cavitation_onset','Cavitation onset screening',True))},
     'st':SimpleNamespace(session_state=state)}
    exec(code,ns)
    return ns,state


def test_column_selection_for_both_fluids_and_both_units():
    ns,_=selection_helpers()
    for fluid in ('Gas','Liquid'):
        result=solve(Config(fluid=fluid),[Stage(),Stage()])
        for sys in SYSTEMS:
            full=labeled_rows(result['stages'],fluid,sys)
            mapping=ns['results_columns'](fluid,sys)
            assert list(mapping.values())==list(full[0])
            chosen={'stage':True,'inlet':True,'pipe_dp':True}
            shown=ns['selected_results'](full,fluid,sys,chosen)
            assert len(shown)==2
            assert list(shown[0])==[mapping[x] for x in chosen]
            assert shown[0][mapping['inlet']]==full[0][mapping['inlet']]


def test_checkbox_selection_persists_and_bulk_actions_affect_current_fluid_only():
    ns,ss=selection_helpers()
    ns['update_results_selection']('Gas',True)
    assert ss['result_show_pipe_sonic'] is True
    assert ss['result_show_stage'] is True
    ss['result_show_mach_out']=False
    ns['update_results_selection']('Liquid',False)
    assert ss['result_show_mach_out'] is False
    assert ss['result_show_cavitation_onset'] is False
    assert ss['result_show_pipe_sonic'] is True
    ns['update_results_selection']('Gas',False)
    assert ss['result_show_pipe_sonic'] is False


def test_no_selection_gives_empty_row_dicts():
    ns,_=selection_helpers()
    result=solve(Config(),[Stage()])
    row=labeled_rows(result['stages'],'Gas','SI')
    assert ns['selected_results'](row,'Gas','SI',{})==[{}]
