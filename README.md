# sat-mf-cmg-instrument-model

The instrument model for the MF SATs that was used for the 2026
Commissioning Paper (add arXiv link here when it exists) and the associated Python scripts needed to run the models for all the different configurations used in the paper.

## Analyses

There are two main analysis scripts in this repository that use `jbolo` models to predict performance metrics measured in the paper and compare the outputs to the measurements from the telescopes.

### Model Setup

`V_MFCMG_Lower` / `V_MFCMG_Upper` are the base models for the MF SAT telescopes
and are intended to bracket the range of expected performance. There are also three
additional configuration files in `model/satp*_params.yaml` that contain the per-telescope
and per-wafer parameters. These parameters are based on in-lab detector
characterization ([Dutcher et al. 2023](https://arxiv.org/abs/2311.05583)) as well as differences
in the configuration of the telescopes on-site.

### Scripts

- **`smcim-model-plots`** -- Builds all of the per-wafer figures in the paper
  by running all the per-wafer models for each telescope: detector NEP,
  photometric calibration and optical efficiency, photon NEP and
  optical loading implied from the measured NEP, and calibration /
  loading vs detector efficiency. Reads `paper_data/noise_data_*.npy` and
  `paper_data/abscal_data_*.npy`; writes `plots/{save_key}_{nep,abscal,
  photon_nep,optical_loading,optical_loading_compare,reponse}.pdf` and
  prints loading/efficiency summaries.

- **`smcim-net-vs-pwv`** -- Predicts the telescope NET as a function of PWV.
  Sweeps PWV at fixed elevation, runs the per-wafer models at each step
  (using the measured per-wafer/band yield-vs-PWV), and combines the
  wafers into a per-telescope NET(PWV) band by inverse-variance weighting.
  Plots that band on its own and overlaid on the measured PWV-binned
  telescope NET (`paper_data/obs_aman_<telescope>_<run_tag>.h5`). The
  expensive model sweep is cached to `paper_data/net_vs_pwv_{save_key}.npy`;
  `--recompute` forces a fresh sweep, `--use-cached` plots from the cache
  without running jbolo.

## Layout

| path | what |
|------|------|
| `model/` | jbolo base sims (`V_MFCMG_Lower` / `V_MFCMG_Upper`) and per-telescope wafer configs (`satp*_params.yaml`) |
| `paper_data/` | paper analysis results used for model comparisons, and cached outputs from model runs in this repository |
| `plots/` | output figures, including many used in the paper |
| `src/smcim/` | the importable library (`pip install -e .`) |
| `src/smcim/cli/` | entry points -- one `main()` per analysis |
| `scripts/` | thin wrappers that call `smcim.cli.*` (run from a checkout without installing the console scripts) |
| `configs/` | the shared YAML config (`config.yaml`); every analysis reads the same file |

## Install

Python >= 3.10. Everything is on PyPI (`numpy`, `matplotlib`, `astropy`,
`sotodlib`, `socolors`, ...) except **jbolo**, which comes from this fork's
[v0.1 release](https://github.com/kmharrington/jbolo/releases/tag/v0.1)
-- the version used for the paper. 

jbolo needs two things that are not in its pip package: the aperture
correction tables (`ApertureFuncs/`, in the repo) and Charlie Hill's
atmosphere model (`atmos/atm_20201217.hdf5`, ~1.1 GB, downloaded
separately). Both are found at runtime via `$JBOLO_PATH`, so install
jbolo from a checkout of that tag:

```
git clone --branch v0.1 https://github.com/kmharrington/jbolo ~/software/jbolo
curl -L https://portal.nersc.gov/cfs/sobs/jbolo/atmos/atm_20201217.hdf5 \
     -o ~/software/jbolo/atmos/atm_20201217.hdf5
pip install ~/software/jbolo
```

Then install this package (pulls the PyPI dependencies):

```
pip install .          # or -e . for a checkout you'll edit
```

The config's `environment.env_vars` block points `JBOLO_PATH` at
`~/software/jbolo` and `JBOLO_MODELS_PATH` at this repo's `model/`; edit
it (or `SMCIM_ROOT` / the config `root:` key) if your checkouts live
elsewhere.

## Running

All analyses share `configs/config.yaml`. It will need to be edited for your 
specific install paths. Set `$SMCIM_ROOT` or put path to this cloned repo in the config's top-level `root:` key.

```
# per-wafer model plots (NEP, abscal, photon NEP, optical loading, ...)
smcim-model-plots  configs/config.yaml

# telescope NET vs PWV: model band + model-vs-measured overlay
smcim-net-vs-pwv   configs/config.yaml               # compute if no cache, else load
smcim-net-vs-pwv   configs/config.yaml --recompute   # force recompute + overwrite cache
smcim-net-vs-pwv   configs/config.yaml --use-cached  # require cache, never run jbolo

# atmospheric efficiency over a PWV x elevation grid
smcim-atmosphere   configs/config.yaml
```

The `scripts/*.py` wrappers are equivalent, e.g.
`python scripts/net_vs_pwv.py configs/config.yaml --use-cached`.

## Atmospheric Transmission

One additional script in this repo: **`smcim-atmosphere`**. Calculates the band-averaged atmospheric efficiency over a PWV x elevation grid, from the base sim with no per-wafer configs. Writes `paper_data/atmosphere_model.npy` and `plots/atmosphere_model.png`.

### AI Acknowledgement
I've used Claude to help convert a bunch of the original analysis scripts I used to do this work into something that is hopefully easier for others to run and look through.  
