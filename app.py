"""PURPL Pressure Ladder Studio — Streamlit UI for the serial fluid solver."""
import json
from dataclasses import asdict
from html import escape

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from solver import Config, Stage, solve, validate

st.set_page_config(page_title='PURPL | Pressure Ladder', page_icon='⚙️', layout='wide', initial_sidebar_state='expanded')

DUSK='#181618'; STARDUST='#9100FF'; MOON='#FFFFFF'; GOLD='#DBC885'
FIELDS=tuple(asdict(Config()))
STAGE_FIELDS=tuple(asdict(Stage()))


def setup_state():
    ss=st.session_state
    if 'model_config' not in ss:
        ss.model_config=asdict(Config())
    if 'model_stages' not in ss:
        ss.model_stages=[asdict(Stage()) for _ in range(3)]
    for field in FIELDS:
        ss.setdefault('cfg_'+field,ss.model_config[field])
    ss.setdefault('stage_count',len(ss.model_stages))
    for i, stage in enumerate(ss.model_stages):
        for field in STAGE_FIELDS:
            ss.setdefault(f'stage_{i}_{field}',stage[field])


def resize_stages():
    n=st.session_state.stage_count
    stages=st.session_state.model_stages
    if len(stages)<n:
        stages.extend(asdict(Stage()) for _ in range(n-len(stages)))
    for i, stage in enumerate(stages[:n]):
        for field, value in stage.items():
            st.session_state.setdefault(f'stage_{i}_{field}', value)
    # Do not throw away hidden stages when decreasing the stage count.
    st.session_state.pop('result',None)


def configuration():
    ss=st.session_state
    c=Config(**{field:ss['cfg_'+field] for field in FIELDS})
    stages=[Stage(**{field:ss[f'stage_{i}_{field}'] for field in STAGE_FIELDS})
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
    for f,v in asdict(config).items(): ss['cfg_'+f]=v
    for i,s in enumerate(stages):
        for f,v in asdict(s).items(): ss[f'stage_{i}_{f}']=v
    ss.stage_count=len(stages)
    ss.pop('result',None)


def system_svg(stages, gas=True):
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
            f'<text x="{(x+right)/2:.1f}" y="{center+radius+71}" text-anchor="middle" fill="#D3D0CB" font-size="11">L = {s.pipe_l_m:g} m</text>',
            f'<text x="{x:.1f}" y="{center-radius-29}" text-anchor="middle" fill="{GOLD}" font-size="11">Ø {s.orifice_d_mm:g} mm</text>',
            f'<text x="{(x+right)/2:.1f}" y="{center-radius-14}" text-anchor="middle" fill="#D3D0CB" font-size="11">Pipe Ø {s.pipe_d_mm:g} mm</text>',
        ])
    elements.append(f'<path d="M {width-74} {center} l 20 0 m -9 -8 l 9 8 -9 8" fill="none" stroke="{GOLD}" stroke-width="2"/>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {h}" style="width:100%;min-width:{min(width,500)}px;height:auto" role="img" aria-label="Serial flow system with {n} orifices">'+''.join(elements)+'</svg>'


setup_state()
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
    st.header('01 / Fluid & boundaries')
    st.radio('Fluid regime', ['Gas','Liquid'],key='cfg_fluid',horizontal=True)
    st.number_input('Supply pressure · psia',min_value=.01,max_value=100000.,step=1.,key='cfg_inlet_psia')
    st.number_input('Backpressure · psia',min_value=.01,max_value=100000.,step=1.,key='cfg_outlet_psia')
    st.number_input('Stagnation temperature · K',min_value=1.,max_value=5000.,step=1.,key='cfg_temperature_k')
    if st.session_state.cfg_fluid=='Gas':
        st.number_input('Specific heat ratio γ',min_value=1.001,max_value=2.0,step=.01,format='%.3f',key='cfg_gamma')
        st.number_input('Specific gas constant · J/(kg·K)',min_value=.01,max_value=10000.,step=1.,key='cfg_gas_constant')
        st.number_input('Gas viscosity · Pa·s',min_value=1e-9,max_value=1.,step=1e-6,format='%.8f',key='cfg_gas_viscosity')
    else:
        st.number_input('Liquid density · kg/m³',min_value=.01,max_value=30000.,step=1.,key='cfg_liquid_density')
        st.number_input('Liquid viscosity · Pa·s',min_value=1e-9,max_value=100.,step=.0001,format='%.6f',key='cfg_liquid_viscosity')
        st.number_input('Liquid vapor pressure · psia',min_value=0.,max_value=100000.,step=.1,key='cfg_vapor_psia')
    st.caption('Values use stable widget keys to preserve every +/- click and typed edit.')

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
            st.number_input('Orifice Ø · mm',min_value=.001,max_value=10000.,step=.5,key=f'stage_{i}_orifice_d_mm')
            st.number_input('Pipe ID · mm',min_value=.001,max_value=10000.,step=1.,key=f'stage_{i}_pipe_d_mm')
            st.number_input('Pipe length · m',min_value=0.,max_value=100000.,step=.1,key=f'stage_{i}_pipe_l_m')
            st.number_input('Roughness · mm',min_value=0.,max_value=1000.,step=.005,format='%.5f',key=f'stage_{i}_roughness_mm')
    st.markdown('**FLOW PATH / SCHEMATIC**')
    try:
        _,stages=configuration()
        svg=system_svg(stages,st.session_state.cfg_fluid=='Gas')
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
    m1.metric('Mass flow',f"{result['mass_flow_kg_s']:.6g} kg/s")
    m2.metric('Orifice choke candidates',len(result['orifice_choke_points']))
    m3.metric('Fanno choke candidates',len(result['pipe_choke_points']))
    if result['nodes_psia'][-1]>result['specified_backpressure_psia']+1e-3:
        st.info('Choked outlet: calculated pipe exit static pressure exceeds the imposed backpressure.')
    st.line_chart(pd.DataFrame({'Pressure · psia':result['nodes_psia']}),color=STARDUST)
    st.dataframe(pd.DataFrame(result['stages']),hide_index=True,use_container_width=True)
    for alert in result['alerts']: st.warning(alert)
    st.download_button('Download results · JSON',json.dumps(result,indent=2),file_name='purpl_results.json',mime='application/json')
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
