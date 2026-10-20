# Pressure Ladder Studio

Browser-based, steady-state serial fluid-flow pressure ladder simulator. Supports an unlimited-in-the-UI number of stages up to a safety limit of 30, each with an orifice and downstream pipe.

## Start locally

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Streamlit displays a localhost address. To publish under a shared URL, push this folder to GitHub and select `app.py` on Streamlit Community Cloud. No secrets needed.

## Input / output
- Supply and backpressure: **absolute psia** (not psig).
- Temperature: K (gas stagnation temperature assumed constant).
- Pipe IDs, orifice diameters, and roughness: mm. Pipe lengths: m.
- Gas: gamma, specific R (J/kg/K), dynamic viscosity (Pa s).
- Liquid: density (kg/m³), viscosity (Pa s), vapor pressure (psia), empirical FL and Fstart.
- Each row: restriction, then pipe; no tees, manifolds or branches.
- Output includes node pressures, mass flow, per-stage Darcy factors, Mach, Fanno f_D L/D, choking indicators, and JSON export.

## Physics and limitations
The gas pipe uses the **subsonic Fanno equation**, with Darcy friction factor:

```
F(M) = (1-M^2)/(gamma M^2) + (gamma+1)/(2 gamma)
       * ln[(gamma+1)M^2/(2+(gamma-1)M^2)]
F(M_in) - F(M_out) = f_D L/D
```

It computes local gas Reynolds number from `mdot*D/(A*mu)` and a laminar / Haaland turbulent Darcy factor. For a specified trial mass flow, downstream static pressure determines outlet Mach, clipped at M=1 when backpressure is below the sonic exit requirement; Fanno is then integrated upstream. A pipe can therefore be flagged as an **additional choke candidate** independently of the orifices. Friction is assumed constant along each pipe (constant mass flux, viscosity and geometry). Each gas restriction uses an equivalent-jet isentropic mass-flow model plus empirical permanent-loss fraction inherited from the original implementation.

**Important engineering limitations:** This is a preliminary steady-state screening tool, not a rigorous network solver or certified design calculator. At choking, the simplified backward-pressure coupling (especially if there are several separated chokes) is not a full coupled compressible network solution. It does not resolve shocks, non-isentropic mixing, nozzle/vena-contracta geometry, full stagnation-pressure bookkeeping through junctions, heat transfer, real-fluid EOS, liquid flashing, downstream pressure recovery interactions, branching or time-dependent tank blowdown. In particular the gas pressure-recovery factor is adapted from an incompressible relationship and is **not validated for high pressure-ratio gas restrictions**. A pipe with nonzero length can have its sonic limit at the exit; the tool does not model normal shocks or supersonic pipe flow. Sonic detection at a pipe exit can be saturated at backpressures below critical. Do not rely on it alone for flight hardware, high-pressure safety decisions, or cavitation-critical systems. Validate against test data or higher-fidelity CFD.

## Files
- `app.py`: Streamlit GUI
- `solver.py`: importable physics model (no Streamlit dependency)
- `tests/test_solver.py`: unit tests including Fanno inverse identity, geometry effects, and choke flags
- `legacy_reference.py`: archived original simulator from Oct 14, 2026
- `.streamlit/config.toml`: visual theme
- `sample_system.json`: example UI configuration

Run `pytest -q` for numerical tests, and `streamlit run app.py` to inspect UI.


## PURPL interface revision (October 20, 2026)

- Official brand colors used: Dusk `#181618`, Stardust `#9100FF`, Moon `#FFFFFF`, and Old Gold `#DBC885`; titles use Chakra Petch and other text uses Roboto Mono loaded using Google Fonts (fallback when offline).
- The fluid/boundary numeric fields use persistent Streamlit keys and do **not** pass a re-initializing `value=` on each rerun, preventing stale-value feedback on plus/minus controls.
- Stage count is adjustable from 1 through 12. Each stage has editable orifice and pipe geometry, friction roughness, and Cd; liquid mode additionally has FL and cavitation-onset sliders.
- The serial pipe and orifice schematic is rendered as scalable SVG and updated when geometry changes. It is illustrative rather than a CAD drawing.
- Existing `solver.py` numerical calculation is unchanged by this UI revision.
- To deploy: commit all project files to GitHub, then on Streamlit Community Cloud select `app.py` as the entrypoint. `requirements.txt` is at the repository root.
- Validation: `python -m compileall -q app.py solver.py` and `python -m pytest -q` (13 tests). Solver and extracted UI state/diagram functions were tested. Browser-level Streamlit automation was **not** possible in the packaging environment because Streamlit was unavailable and package downloads were blocked. After deployment, visually test numeric +/- fields, stage count and import/export flows.

## v3 — Unit systems, diagnostics, and exports

The `Unit system` dropdown at the top of the Streamlit sidebar changes all editable physical-property fields, boundary conditions, stage geometry, schematic dimensions, chart pressures, result table pressures, and flow-rate readout between:

- **SI:** kPa absolute, K, mm, m, mm roughness, kg/m³, mPa·s, J/(kg·K), kg/s.
- **US customary:** psia, °F, in, ft, in roughness, lbm/ft³, cP, ft·lbf/(lbm·°R), lbm/s.

The solver continues to use the original `Config` and `Stage` canonical units defined by `solver.py`; the UI's `units.py` performs all conversions. Imported configuration JSON remains canonical to preserve compatibility with v2. Results JSON exports canonical values; the downloadable CSV uses selected display units.

**Fanno diagnostics:** `fanno_capacity` is the Darcy friction parameter F(M_in); `fanno_used` = f_D L/D; `fanno_remaining` = F(M_out). Utilization is `used/capacity`, and the pipe choking indicator is set when the pipe exit is at Mach 1 under the imposed-backpressure approximation. A large pressure drop alone is not proof of choking. On very long pipes utilization can approach 100% while the outlet Mach remains subsonic because F(M_in) becomes extremely large at low inlet Mach numbers.

**Important physics limitations:** This is a serial screening model, not a fully coupled multichoke gas-flow model. The nozzle/orifice pressure-recovery approximation and stage static/stagnation state coupling are not experimentally validated. The boundary-pressure floor used when a pipe would become sonic is approximate and cannot resolve complex shocks, boundary-pressure-dependent expansions, or multiple simultaneously choked elements. Verify critical engineering predictions independently before relying on them.

### v4 — Selectable stage results

The **Results display · Column checkboxes** panel appears after running the solver.
Use the per-output checkboxes to choose the visible table columns, or **Select all** / **Clear all** to toggle outputs for the current fluid regime. The selection persists through reruns and unit-system changes. The CSV export includes exactly the visible columns in the active unit system. The raw JSON export always contains the full set of engineering results, regardless of visibility selections.

### Updating an existing Community Cloud installation

Replace the project files in your existing GitHub repository (including `app.py`) and commit to `main`. Community Cloud will redeploy automatically.
