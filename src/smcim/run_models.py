"""Apply per-telescope and per-wafer config overrides onto a jbolo base
sim and run it, and drive that over every wafer of every telescope.

It also locates the base sims and per-telescope config yamls under
``$JBOLO_MODELS_PATH`` (:func:`sim_list`, :func:`telescope_configs`) and
runs the full per-wafer / per-telescope grid (:func:`run_all_models`).
"""
import os

import yaml

import jbolo.jbolo_funcs as jf
import jbolo.utils as utils
from jbolo.utils import load_sim

# The Lower/Upper bounding base sims, relative to $JBOLO_MODELS_PATH.
SIM_FILES = {
    "lower": "V_MFCMG_Lower/V_MFCMG_Lower_SAT_MF.yaml",
    "upper": "V_MFCMG_Upper/V_MFCMG_Upper_SAT_MF.yaml",
}

TELESCOPE_CONFIG_FILES = {
    "satp1_iso": "satp1_iso_params.yaml",
    "satp1_retrofit": "satp1_retrofit_params.yaml",
    "satp3_iso": "satp3_iso_params.yaml",
}


def _models_dir():
    return os.environ.get("JBOLO_MODELS_PATH", "")


def sim_list():
    """{'lower': path, 'upper': path} for the bounding base sims."""
    d = _models_dir()
    return {k: os.path.join(d, v) for k, v in SIM_FILES.items()}


def telescope_configs():
    """{telescope: path} for the per-telescope wafer config yamls."""
    d = _models_dir()
    return {k: os.path.join(d, v) for k, v in TELESCOPE_CONFIG_FILES.items()}


def apply_telescope_configs(sim, configs):
    """
    telescope:
        bolo_config:
            straight numbers to update
        optical_elements:
            values to update but using dictionary update
    """
    assert 'telescope' in configs, f"telescope not in configurations"
    tel_configs = configs['telescope']
    if 'bolo_config' in tel_configs:
        for k in tel_configs['bolo_config']:
            sim['bolo_config'][k] = tel_configs['bolo_config'][k]

    if 'optical_elements' in tel_configs:
        for optic in tel_configs['optical_elements']:
            assert optic in sim['optical_elements'], f"cannot find {optic} to update"
            sim_optic = sim['optical_elements'][optic]
            sim_optic.update( tel_configs['optical_elements'][optic] )
            sim['optical_elements'][optic] = sim_optic

def apply_psat( ch_cfgs, T_bath, T_c):
    n = ch_cfgs['n']
    kappa = ch_cfgs['kappa']

    ch_cfgs['psat'] = kappa*(T_c**n - T_bath**n)

def apply_Gdynamic(ch_cfgs, T_bath, T_c):
    n = ch_cfgs['n']
    psat = ch_cfgs['psat']

    ch_cfgs['G_dynamic'] = psat*n * T_c**(n-1)/(T_c**n - T_bath**n)

def apply_wafer_configs(sim, configs, wafer, update_det_params=True):
    """
    apply per wafer configurations, these configs are in the form:
    note that the per channel configs are updated directly into sim['channels']
    If update_det_params is true, then kappa, n, and T_c are used with T_bath
    to calculate the psat of the detectors

    if update_det_params is false, psat is pulled straight from the
    configuration file

    if  G_dynamic is in the config, set it as explicitly specified

    wafers:
      wafer_name:
        R_n: X             ## measured in UXM Dashboard
        T_c: X             ## measured in UXM Dashboard
        yield: X           ## measured in UXM Dashboard
        psat_tbath: X      ## the bath temperature where Psat was measured
        MF_X: (entry for MF_1 and MF_2)
          det_eff: X       ## measured adjusted for v4r1 passbands
          psat: X          ## measured in UXM Dashboard
          kappa: X         ## measured in UXM Dashboard
          G_dynamic: X     ## measured in UXM Dashboard
          n: X             ## measured in UXM Dashboard
          NEP_dark: X      ## measured in UXM Dashboard
          pton_det_eff: X  ## measured in UXM Dashboard
    """
    assert wafer in configs['wafers'], f"{wafer} not in configurations"
    wafer_configs = configs['wafers'][wafer]

    ## R_bolo assumed to be 0.5 R_n
    sim['bolo_config']['R_bolo'] = 0.5*wafer_configs.get(
        "R_n", 2*sim['bolo_config']['R_bolo']
    )
    sim['bolo_config']['yield'] = wafer_configs.get(
        "yield", sim['bolo_config']['yield']
    )
    sim['bolo_config']['T_c'] = wafer_configs.get(
        'T_c', sim['bolo_config']['T_c']
    )

    for ch in sim['channels']:
        assert ch in wafer_configs, f"{ch} not found in {wafer} configs"

        sim['channels'][ch].update( wafer_configs[ch] )
        if update_det_params:
            apply_psat(
                sim['channels'][ch],
                sim['bolo_config']['T_bath'],
                sim['bolo_config']['T_c']
            )
            sim['bolo_config']['psat_method'] = 'specified'
        elif 'psat' in wafer_configs[ch]:
            sim['bolo_config']['psat_method'] = 'specified'

        if 'G_dynamic' in wafer_configs[ch]:
            apply_Gdynamic(
                sim['channels'][ch],
                sim['bolo_config']['T_bath'] ,
                sim['bolo_config']['T_c']
            )
            sim['bolo_config']['G_dynamic_method'] = 'specified'


def run_wafer(
        sim_file, configs, wafer, additional_functions=[],
        wafer_kwargs={}
    ):
    sim = utils.load_sim( sim_file )
    apply_telescope_configs(sim, configs)
    apply_wafer_configs(sim, configs, wafer, **wafer_kwargs)
    sim['version']['wafer'] = wafer

    for func in additional_functions:
        func(sim)

    jf.run_optics(sim)
    jf.run_bolos(sim)
    return sim


def run_all_models(sims=None, tel_configs=None, additional_functions=()):
    """Run every wafer of every telescope for both bounding sims, plus the
    two base sims on their own.

    Returns ``(base_sims, per_wafer_models)`` where
    ``per_wafer_models[telescope][kind][wafer]`` is a finished jbolo sim
    dict and ``base_sims[kind]`` is the per-kind base sim with no
    per-wafer configs applied.
    """
    sims = sims or sim_list()
    tel_configs = tel_configs or telescope_configs()
    additional_functions = list(additional_functions)

    per_wafer_models = {k: {kind: {} for kind in sims} for k in tel_configs}
    for k in per_wafer_models:
        configs = yaml.safe_load(open(tel_configs[k], "r"))
        for wafer in configs["wafers"]:
            for kind in sims:
                per_wafer_models[k][kind][wafer] = run_wafer(
                    sims[kind], configs, wafer,
                    additional_functions=additional_functions,
                )

    base_sims = {}
    for kind in sims:
        sim = load_sim(sims[kind])
        for func in additional_functions:
            func(sim)
        jf.run_optics(sim)
        jf.run_bolos(sim)
        base_sims[kind] = sim
    return base_sims, per_wafer_models
