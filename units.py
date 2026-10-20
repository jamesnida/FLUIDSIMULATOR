"""Global display conversions. Solver configuration always remains in legacy canonical SI-compatible units."""
from dataclasses import asdict
from solver import Config, Stage, PSI

SYSTEMS=('SI','US customary')
# canonical config: psia, K, J/kg/K, Pa.s, kg/m3
# canonical geometry: mm, m
UNITS={
 'SI':{
  'pressure':('kPa',PSI/1000.,0.0), 'temperature':('K',1.,0.),
  'diameter':('mm',1.,0.),'length':('m',1.,0.), 'roughness':('mm',1.,0.),
  'density':('kg/m³',1.,0.), 'viscosity':('mPa·s',1000.,0.),
  'gas_constant':('J/(kg·K)',1.,0.),'mass_flow':('kg/s',1.,0.)},
 'US customary':{
  'pressure':('psia',1.,0.), 'temperature':('°F',1.8,-459.67),
  'diameter':('in',1/25.4,0.),'length':('ft',3.280839895013123,0.),
  'roughness':('in',1/25.4,0.),
  'density':('lbm/ft³',0.0624279605761,0.),
  'viscosity':('cP',1000.,0.),
  'gas_constant':('ft·lbf/(lbm·°R)',0.185862535179,0.),
  'mass_flow':('lbm/s',2.20462262185,0.)}}
CONFIG_KINDS={'inlet_psia':'pressure','outlet_psia':'pressure','vapor_psia':'pressure',
 'temperature_k':'temperature','gas_constant':'gas_constant','gas_viscosity':'viscosity',
 'liquid_density':'density','liquid_viscosity':'viscosity'}
STAGE_KINDS={'orifice_d_mm':'diameter','pipe_d_mm':'diameter','pipe_l_m':'length','roughness_mm':'roughness'}

def to_display(value, kind, system):
    _, scale, offset=UNITS[system][kind]
    # °F = K*1.8 - 459.67
    return float(value)*scale+offset

def to_canonical(value, kind, system):
    _, scale, offset=UNITS[system][kind]
    return (float(value)-offset)/scale

def unit(kind,system):return UNITS[system][kind][0]

def convert_config(c,system):
    return {k:to_display(v,CONFIG_KINDS[k],system) if k in CONFIG_KINDS else v for k,v in asdict(c).items()}

def convert_stage(s,system):
    return {k:to_display(v,STAGE_KINDS[k],system) if k in STAGE_KINDS else v for k,v in asdict(s).items()}

def read_config(vals,system):
    return Config(**{k:to_canonical(v,CONFIG_KINDS[k],system) if k in CONFIG_KINDS else v for k,v in vals.items()})

def read_stage(vals,system):
    return Stage(**{k:to_canonical(v,STAGE_KINDS[k],system) if k in STAGE_KINDS else v for k,v in vals.items()})

def labeled_rows(rows,fluid,system):
    p=unit('pressure',system)
    dp_unit='psi' if system=='US customary' else 'kPa'
    def pressure(x):return round(to_display(x/PSI,'pressure',system),4)
    out=[]
    for r in rows:
        d={'Stage':r['stage'],f'Inlet static pressure ({p})':pressure(r['p_in']),
           f'Outlet static pressure ({p})':pressure(r['p_out']),
           f'Orifice ΔP ({dp_unit})':pressure(r['orifice_dp']),
           f'Pipe ΔP ({dp_unit})':pressure(r['pipe_dp']),
           'Re (dimensionless)':round(r['re'],1),
           'Darcy friction factor (dimensionless)':round(r['friction'],5)}
        if fluid=='Gas':
            d.update({'Mach inlet (dimensionless)':round(r['mach_in'],5),
              'Mach outlet (dimensionless)':round(r['mach_out'],5),
              'Fanno capacity fD·L/D (dimensionless)':round(r['fanno_capacity'],4),
              'Fanno consumed fD·L/D (dimensionless)':round(r['fanno_used'],4),
              'Fanno remaining (dimensionless)':round(r['fanno_remaining'],4),
              'Fanno utilization (%)':round(100*r['fanno_utilization'],2),
              'Pipe sonic (Mach 1)':r['pipe_choked'],
              'Orifice sonic candidate':r['orifice_choked']})
        else:
            d.update({'Orifice cavitation limit':r['orifice_choked'],
                      'Cavitation onset screening':r['cavitation_onset']})
        out.append(d)
    return out
