"""PURPL Pressure Ladder Studio — Streamlit UI for the serial fluid solver."""
import json
from dataclasses import asdict
from html import escape

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from solver import Config, Stage, solve, validate, PSI
from units import (SYSTEMS,CONFIG_KINDS,STAGE_KINDS,unit,to_display,to_canonical,
                   convert_config,convert_stage,read_config,read_stage,labeled_rows)

st.set_page_config(page_title='PURPL | Pressure Ladder', page_icon='⚙️', layout='wide', initial_sidebar_state='expanded')

DUSK='#181618'; STARDUST='#9100FF'; MOON='#FFFFFF'; GOLD='#DBC885'
FIELDS=tuple(asdict(Config()))
STAGE_FIELDS=tuple(asdict(Stage()))


def setup_state():
    ss=st.session_state
    ss.setdefault('unit_system','SI')
    if 'model_config' not in ss:
        ss.model_config=asdict(Config())
    if 'model_stages' not in ss:
        ss.model_stages=[asdict(Stage()) for _ in range(3)]
    for field in FIELDS:
        ss.setdefault('cfg_'+field,convert_config(Config(**ss.model_config),ss.unit_system)[field])
    ss.setdefault('stage_count',len(ss.model_stages))
    for i, stage in enumerate(ss.model_stages):
        for field in STAGE_FIELDS:
            ss.setdefault(f'stage_{i}_{field}',convert_stage(Stage(**stage),ss.unit_system)[field])


def resize_stages():
    n=st.session_state.stage_count
    stages=st.session_state.model_stages
    if len(stages)<n:
        stages.extend(asdict(Stage()) for _ in range(n-len(stages)))
    for i, stage in enumerate(stages[:n]):
        for field, value in stage.items():
            st.session_state.setdefault(f'stage_{i}_{field}', convert_stage(Stage(**stage),st.session_state.unit_system)[field])
    # Do not throw away hidden stages when decreasing the stage count.
    st.session_state.pop('result',None)


def configuration():
    ss=st.session_state
    c=read_config({field:ss['cfg_'+field] for field in FIELDS},ss.unit_system)
    stages=[read_stage({field:ss[f'stage_{i}_{field}'] for field in STAGE_FIELDS},ss.unit_system)
            for i in range(ss.stage_count)]
    return c,stages


def import_system(data):
    """Atomically validate and then replace every widget key to prevent stale values."""
    config=Config(**data['config'])
    stages=[Stage(**record) for record in data['stages']]
    if not 1<=len(stages)<=12:
        raise ValueError('A system must have between 1 and 12 stages.')
    validate(config,stages)
    ss=st.session_state
    ss.model_config=asdict(config)
    ss.model_stages=[asdict(s) for s in stages]
    for f,v in asdict(config).items(): ss['cfg_'+f]=convert_config(config,ss.unit_system)[f]
    for i,s in enumerate(stages):
        for f,v in asdict(s).items(): ss[f'stage_{i}_{f}']=convert_stage(s,ss.unit_system)[f]
    ss.stage_count=len(stages)
    ss.pop('result',None)


def change_units():
    """Convert live widget values before they are recreated during a Streamlit rerun."""
    ss=st.session_state
    old=ss.get('_previous_unit_system','SI')
    new=ss.unit_system
    if old==new: return
    for field,kind in CONFIG_KINDS.items():
        key='cfg_'+field
        if key in ss:
            ss[key]=to_display(to_canonical(ss[key],kind,old),kind,new)
    for i in range(len(ss.model_stages)):
        for field,kind in STAGE_KINDS.items():
            key=f'stage_{i}_{field}'
            if key in ss:
                ss[key]=to_display(to_canonical(ss[key],kind,old),kind,new)
    ss._previous_unit_system=new
    ss.pop('result',None)


def system_svg(stages, gas=True, display_system='SI'):
    """Standalone vector technical drawing, dimensions annotated to each stage."""
    n=len(stages); width=max(840, n*205+160); center=130; h=265
    x0=75; dx=(width-150)/n
    elements=[f'<rect x="0" y="0" width="{width}" height="{h}" rx="12" fill="#211A26"/>',
              f'<text x="25" y="28" fill="{GOLD}" font-size="12">FLOW DIRECTION  →</text>',
              f'<text x="{width-25}" y="28" text-anchor="end" fill="#D3D0CB" font-size="11">NOT TO SCALE · SERIAL MODEL</text>']
    for i,s in enumerate(stages):
        left=x0+i*dx; right=left+dx
        x=left+dx*.37
        radius=28
        hole=max(5,min(23,23*s.orifice_d_mm/max(s.pipe_d_mm,.001)))
        # Pipe upper and lower walls, thin line drawing; orifice annular plate spans the bore.
        for y in [center-radius,center+radius]:
            elements.append(f'<line x1="{left:.1f}" y1="{y}" x2="{right:.1f}" y2="{y}" stroke="#FAF7FF" stroke-width="3"/>')
        elements.extend([
            f'<rect x="{x-5:.1f}" y="{center-radius-11}" width="10" height="{radius+11-hole}" fill="{STARDUST}"/>',
            f'<rect x="{x-5:.1f}" y="{center+hole}" width="10" height="{radius+11-hole}" fill="{STARDUST}"/>',
            f'<line x1="{x:.1f}" y1="{center+radius+17}" x2="{x:.1f}" y2="{center+radius+35}" stroke="{GOLD}" stroke-width="1"/>',
            f'<text x="{x:.1f}" y="{center+radius+50}" text-anchor="middle" fill="{MOON}" font-size="13">O{i+1:02}</text>',
            f'<text x="{(x+right)/2:.1f}" y="{center+radius+71}" text-anchor="middle" fill="#D3D0CB" font-size="11">L = {to_display(s.pipe_l_m,'length',display_system):.4g} {unit('length',display_system)}</text>',
            f'<text x="{x:.1f}" y="{center-radius-29}" text-anchor="middle" fill="{GOLD}" font-size="11">Ø {to_display(s.orifice_d_mm,'diameter',display_system):.4g} {unit('diameter',display_system)}</text>',
            f'<text x="{(x+right)/2:.1f}" y="{center-radius-14}" text-anchor="middle" fill="#D3D0CB" font-size="11">Pipe Ø {to_display(s.pipe_d_mm,'diameter',display_system):.4g} {unit('diameter',display_system)}</text>',
        ])
    elements.append(f'<path d="M {width-74} {center} l 20 0 m -9 -8 l 9 8 -9 8" fill="none" stroke="{GOLD}" stroke-width="2"/>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {h}" style="width:100%;min-width:{min(width,500)}px;height:auto" role="img" aria-label="Serial flow system with {n} orifices">'+''.join(elements)+'</svg>'


# Checkboxes use stable identifiers rather than unit-dependent column headings.
RESULT_FIELDS = {
    'all': (
        ('stage', 'Stage', True),
        ('inlet', 'Inlet static pressure', True),
        ('outlet', 'Outlet static pressure', True),
        ('orifice_dp', 'Orifice pressure drop', True),
        ('pipe_dp', 'Pipe pressure drop', True),
        ('re', 'Reynolds number', False),
        ('friction', 'Darcy friction factor', False),
    ),
    'Gas': (
        ('mach_in', 'Pipe inlet Mach', True),
        ('mach_out', 'Pipe outlet Mach', True),
        ('capacity', 'Fanno capacity', False),
        ('consumed', 'Fanno consumed', False),
        ('remaining', 'Fanno remaining', False),
        ('utilization', 'Fanno utilization', True),
        ('pipe_sonic', 'Pipe sonic', True),
        ('orifice_sonic', 'Orifice sonic candidate', True),
    ),
    'Liquid': (
        ('cavitation_limit', 'Orifice cavitation limit', True),
        ('cavitation_onset', 'Cavitation onset screening', True),
    ),
}


def results_columns(fluid, system):
    """Map stable selection IDs to display-specific headers from units.labeled_rows."""
    pressure = unit('pressure', system)
    dp = 'psi' if system == 'US customary' else 'kPa'
    common = [
        ('stage', 'Stage'),
        ('inlet', f'Inlet static pressure ({pressure})'),
        ('outlet', f'Outlet static pressure ({pressure})'),
        ('orifice_dp', f'Orifice ΔP ({dp})'),
        ('pipe_dp', f'Pipe ΔP ({dp})'),
        ('re', 'Re (dimensionless)'),
        ('friction', 'Darcy friction factor (dimensionless)'),
    ]
    if fluid == 'Gas':
        extra = [
            ('mach_in', 'Mach inlet (dimensionless)'),
            ('mach_out', 'Mach outlet (dimensionless)'),
            ('capacity', 'Fanno capacity fD·L/D (dimensionless)'),
            ('consumed', 'Fanno consumed fD·L/D (dimensionless)'),
            ('remaining', 'Fanno remaining (dimensionless)'),
            ('utilization', 'Fanno utilization (%)'),
            ('pipe_sonic', 'Pipe sonic (Mach 1)'),
            ('orifice_sonic', 'Orifice sonic candidate'),
        ]
    else:
        extra = [('cavitation_limit', 'Orifice cavitation limit'),
                 ('cavitation_onset', 'Cavitation onset screening')]
    return dict(common + extra)


def selected_results(rows, fluid, system, selection):
    """Filter a labeled table without modifying underlying simulation output."""
    mapping = results_columns(fluid, system)
    columns = [header for identifier, header in mapping.items() if selection.get(identifier, False)]
    return [{header: row[header] for header in columns} for row in rows]


def update_results_selection(fluid, checked):
    """Used by Select all / Clear controls; applies only to current-fluid fields."""
    for identifier, _, _ in RESULT_FIELDS['all'] + RESULT_FIELDS[fluid]:
        st.session_state[f'result_show_{identifier}'] = checked


setup_state()
st.session_state.setdefault('_previous_unit_system',st.session_state.unit_system)
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@400;500;600&family=Roboto+Mono:wght@300;400;700&display=swap');
html,body,[data-testid="stApp"], [data-testid="stSidebar"]{background:#181618;color:#ffffff;}
[data-testid="stAppViewContainer"]{background:radial-gradient(ellipse at 95% 0%, #34015B55 0%, transparent 39%), #181618;}
h1,h2,h3,h4{font-family:'Chakra Petch',sans-serif !important;letter-spacing:.035em;}
p,label,small,[data-testid="stMetricLabel"], [data-testid="stMetricValue"]{font-family:'Roboto Mono',monospace !important;}
[data-testid="stSidebar"]{border-right:1px solid #DBC88555;}
[data-testid="stVerticalBlockBorderWrapper"]{border-color:#9100FF55;}
.stButton>button[kind="primary"]{background:#9100FF;color:white;border:1px solid #9100FF;}
[data-testid="stSlider"] [role="slider"]{background:#9100FF;}
hr{border-color:#DBC88555;}
.purpl-eyebrow{font-family:'Roboto Mono';letter-spacing:.24em;color:#DBC885;font-size:.8rem;}
.purpl-rule{height:1px;background:linear-gradient(90deg,#DBC885,#9100FF,transparent);margin:8px 0 18px;}
.purpl-station{font-family:'Chakra Petch';font-weight:600;letter-spacing:.09em;color:#9100FF;font-size:1.1rem;}
</style>""",unsafe_allow_html=True)

st.markdown('<div class="purpl-eyebrow">PURDUE UNIVERSITY ROCKET PROPULSION LABORATORY · FLUID SYSTEMS</div>',unsafe_allow_html=True)
st.title('PURPL / Pressure Ladder Studio')
st.markdown('<div class="purpl-rule"></div>',unsafe_allow_html=True)
st.caption('Steady-state serial network · Fanno gas pipes · liquid cavitation screening · computational inputs in SI-compatible units')

with st.sidebar:
    st.header('00 / Display units')
    st.selectbox('Unit system',SYSTEMS,key='unit_system',on_change=change_units,
                 help='Changes input widgets, chart, table and mass-flow display. Solver calculations stay in SI.')
    u=st.session_state.unit_system
    pu=unit('pressure',u);tu=unit('temperature',u)
    st.header('01 / Fluid & boundaries')
    st.radio('Fluid regime',['Gas','Liquid'],key='cfg_fluid',horizontal=True)
    st.number_input(f'Supply pressure ({pu}, absolute)',min_value=.001,max_value=1e9,step=1.,format='%.4f',key='cfg_inlet_psia')
    st.number_input(f'Backpressure ({pu}, absolute)',min_value=.001,max_value=1e9,step=1.,format='%.4f',key='cfg_outlet_psia')
    st.number_input(f'Stagnation temperature ({tu})',min_value=-459.66 if u=='US customary' else .001,max_value=10000.,step=1.,format='%.3f',key='cfg_temperature_k')
    if st.session_state.cfg_fluid=='Gas':
        st.number_input('Specific heat ratio γ (dimensionless)',min_value=1.001,max_value=2.0,step=.01,format='%.3f',key='cfg_gamma')
        st.number_input(f'Specific gas constant ({unit("gas_constant",u)})',min_value=.00001,max_value=10000.,step=1.,format='%.6f',key='cfg_gas_constant')
        st.number_input(f'Gas viscosity ({unit("viscosity",u)})',min_value=1e-9,max_value=100000.,step=.001,format='%.6f',key='cfg_gas_viscosity')
    else:
        st.number_input(f'Liquid density ({unit("density",u)})',min_value=.00001,max_value=30000.,step=1.,format='%.4f',key='cfg_liquid_density')
        st.number_input(f'Liquid viscosity ({unit("viscosity",u)})',min_value=1e-9,max_value=100000.,step=.01,format='%.6f',key='cfg_liquid_viscosity')
        st.number_input(f'Liquid vapor pressure ({pu}, absolute)',min_value=0.,max_value=1e9,step=.1,format='%.4f',key='cfg_vapor_psia')
    st.caption('All displayed dimensions update on unit-system changes; settings remain persistent across reruns.')

st.header('02 / System geometry')
st.slider('Number of orifices',1,12,key='stage_count',on_change=resize_stages)
st.caption('Each orifice is followed by a pipe section. Scroll horizontally for large systems.')

n=st.session_state.stage_count
# Each column has the same relative width as its schematic station; graphics stay aligned.
with st.container(border=True):
    cols=st.columns(n,gap='small')
    for i,col in enumerate(cols):
        with col:
            st.markdown(f'<div class="purpl-station">ORIFICE {i+1:02}</div>',unsafe_allow_html=True)
            st.slider('Cd',min_value=.1,max_value=1.,step=.01,key=f'stage_{i}_cd',help=f'Discharge coefficient for orifice {i+1}')
            if st.session_state.cfg_fluid=='Liquid':
                st.slider('Recovery FL',min_value=.1,max_value=1.,step=.01,key=f'stage_{i}_fl')
                st.slider('Cavitation onset',min_value=.05,max_value=1.,step=.01,key=f'stage_{i}_fstart')
            st.number_input(f'Orifice Ø ({unit("diameter",u)})',min_value=.000001,max_value=1e7,step=.5 if u=='SI' else .02,format='%.5f',key=f'stage_{i}_orifice_d_mm')
            st.number_input(f'Pipe ID ({unit("diameter",u)})',min_value=.000001,max_value=1e7,step=1. if u=='SI' else .05,format='%.5f',key=f'stage_{i}_pipe_d_mm')
            st.number_input(f'Pipe length ({unit("length",u)})',min_value=0.,max_value=1e8,step=.1 if u=='SI' else .5,format='%.5f',key=f'stage_{i}_pipe_l_m')
            st.number_input(f'Roughness ({unit("roughness",u)})',min_value=0.,max_value=1e6,step=.005 if u=='SI' else .0001,format='%.6f',key=f'stage_{i}_roughness_mm')
    st.markdown('**FLOW PATH / SCHEMATIC**')
    try:
        _,stages=configuration()
        svg=system_svg(stages,st.session_state.cfg_fluid=='Gas',u)
        # SVG image stays crisp and scrolls without clipping as the stage count grows.
        components.html('<div style="overflow-x:auto;background:#211A26;border:1px solid #9100FF55;border-radius:10px;">'+svg+'</div>',height=295,scrolling=False)
    except (ValueError,KeyError) as e:
        st.warning(f'Schematic unavailable: {e}')

st.header('03 / Solver')
c,stages=configuration()
if st.button('▶ Run pressure ladder',type='primary',use_container_width=True):
    try:
        st.session_state.result=solve(c,stages)
        st.session_state.result_signature=json.dumps({'config':asdict(c),'stages':[asdict(s) for s in stages]},sort_keys=True)
    except (ValueError,OverflowError,ZeroDivisionError) as exc:
        st.session_state.pop('result',None)
        st.error(str(exc))

signature=json.dumps({'config':asdict(c),'stages':[asdict(s) for s in stages]},sort_keys=True)
result=st.session_state.get('result') if signature==st.session_state.get('result_signature') else None
if result:
    m1,m2,m3=st.columns(3)
    m1.metric('Mass flow',f"{to_display(result['mass_flow_kg_s'],'mass_flow',u):.6g} {unit('mass_flow',u)}")
    m2.metric('Orifice choke candidates',len(result['orifice_choke_points']))
    m3.metric('Fanno choke candidates',len(result['pipe_choke_points']))
    if result['nodes_psia'][-1]>result['specified_backpressure_psia']+1e-3:
        st.info('Choked outlet: calculated pipe exit static pressure exceeds the imposed backpressure.')
    st.line_chart(pd.DataFrame({f'Static pressure ({pu}, absolute)':[to_display(x,'pressure',u) for x in result['nodes_psia']]}),color=STARDUST)
    st.caption('Fanno capacity and consumption are dimensionless Darcy friction-length parameters (fD·L/D); utilization is consumption / capacity. Choking requires Mach 1, not a fixed pressure-loss percentage.')
    st.subheader('Stage results / Choose outputs')
    st.caption('Tick only the quantities you want to display. Your selection persists when you rerun the model or change units.')
    with st.expander('Results display · Column checkboxes', expanded=True):
        buttons=st.columns([1,1,4])
        if buttons[0].button('Select all',key='result_select_all'):
            update_results_selection(c.fluid,True)
            st.rerun()
        if buttons[1].button('Clear all',key='result_clear_all'):
            update_results_selection(c.fluid,False)
            st.rerun()
        for group_name,definitions in (('Common outputs',RESULT_FIELDS['all']),
                                        ('Gas outputs' if c.fluid=='Gas' else 'Liquid outputs',RESULT_FIELDS[c.fluid])):
            st.markdown(f'**{group_name}**')
            checkbox_cols=st.columns(3)
            for j,(identifier,label,default) in enumerate(definitions):
                key=f'result_show_{identifier}'
                st.session_state.setdefault(key,default)
                with checkbox_cols[j%3]:
                    st.checkbox(label,key=key)
    selections={identifier:st.session_state.get(f'result_show_{identifier}',default)
                for identifier,_,default in RESULT_FIELDS['all']+RESULT_FIELDS[c.fluid]}
    full_rows=labeled_rows(result['stages'],c.fluid,u)
    shown_rows=selected_results(full_rows,c.fluid,u,selections)
    if not any(selections.values()):
        st.info('No outputs selected. Check at least one box above to show the results table and enable CSV export.')
    else:
        displayed_table=pd.DataFrame(shown_rows)
        st.dataframe(displayed_table,hide_index=True,use_container_width=True)
        st.download_button('Download visible columns · CSV (selected units)',
                           displayed_table.to_csv(index=False),file_name='purpl_stage_results.csv',mime='text/csv')
    for alert in result['alerts']: st.warning(alert)
    st.download_button('Download raw solver results · JSON (canonical units)',json.dumps(result,indent=2),file_name='purpl_results.json',mime='application/json')
else:
    st.caption('Press Run pressure ladder to calculate the current geometry and fluid properties.')

st.divider()
st.header('04 / Save or import')
config_file={'config':asdict(c),'stages':[asdict(s) for s in stages]}
st.download_button('Export configuration · JSON',json.dumps(config_file,indent=2),file_name='purpl_system.json',mime='application/json')
upload=st.file_uploader('Import a saved system · JSON',type=['json'])
if upload is not None and st.button('Import configuration'):
    try:
        import_system(json.load(upload))
        st.rerun()
    except (ValueError,KeyError,TypeError,OverflowError) as exc:
        st.error(f'Invalid configuration: {exc}')
st.caption('Engineering limitations: steady serial system; ideal gas with Fanno pipe friction; simplified orifice recovery and liquid cavitation screening; not validated for two-phase flow, shocks, manifolds, or arbitrary branching.')
