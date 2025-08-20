import dataclasses


@dataclasses.dataclass
class NotSubmitTimeInterpolatable:
    """Filename defaults that can not be interpolated at submit-time"""

    content: str


@dataclasses.dataclass
class NoDefault:
    ...
    # placeholder_mapping: dict[str, str] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class NotReadByDefault:
    original_value: str = ""


INPUTFILE_DEFAULTS = {
    "assimilation_nml": {
        "radardata_file": NoDefault(),
        "blacklist_file": "radarblacklist.nc",
        "height_file": "radarheight.nc",
        "dace_namelist_file": "namelist",
    },
    "grid_nml": {
        "dynamics_grid_filename": NoDefault(),
        "radiation_grid_filename": NoDefault(),
        "vertical_grid_filename": NoDefault(),
        "vct_filename": NoDefault(),
    },
    "initicon_nml": {
        "ifs2icon_filename": NotSubmitTimeInterpolatable("<path>ifs2icon_R<nroot>B<jlev>_DOM <idom>.nc"),
        "dwdfg_filename ": NotSubmitTimeInterpolatable("<path>dwdFG_R<nroot>B<jlev>_DOM <idom>.nc"),
        "dwdana_filename": NotSubmitTimeInterpolatable("<path>dwdana_R<nroot>B<jlev>_DOM <idom>.nc"),
        "ana_varnames_map_ file": NoDefault(),
        "fire2d_filename": NotSubmitTimeInterpolatable("gfas2d_emi_<species>_<gridfile>_<yyyymmdd>.nc"),
    },
    "io_nml": {
        "output_nml_dict": NotReadByDefault(""),
        "netcdf_dict": NotReadByDefault(""),
    },
    "limarea_nml": {
        "latbc_filename": NotSubmitTimeInterpolatable("prepiconR<nroot>B<jlev>_<y><m><d><h>.nc"),
        "latbc_path": "./",
        "latbc_boundary_grid": NotReadByDefault(""),
        "latbc_varnames_map_file": NoDefault(),
    },
    "lnd_nml": {
        "sst_td_filename": NotSubmitTimeInterpolatable("<path>SST_<year>_<month>_<gridfile>"),
        "ci_td_filename": NotSubmitTimeInterpolatable("<path>CI_<year>_<month>_<gridfile>"),
    },
    "master_nml": {"model_base_dir": ""},
    "master_model_nml": {"model_namelist_filename": NoDefault()},
    "nwp_phy_nml": {"lrtm_filename": "rrtmg_lw.nc", "cldopt_filename": "ECHAM6_CldOptProps.nc"},
    "parallel_nml": {
        "division_filename": NoDefault(),
    },
    "radiation_nml": {
        "ecrad_data_path": ".",
        "cams_aero_filename": NotSubmitTimeInterpolatable("CAMS_aero_R<nroot()>B<jlev>_DOM<idom>.nc"),
    },
    "run_nml": {
        "restart_filename": NotSubmitTimeInterpolatable("<gridfile>_restart_<mtype>_<rsttime>.nc"),
        "radarnmlfile": NoDefault(),
    },
    "turbdiff_nml": {
        "nwp_extdat_gases_filename": "upatmo_gases_chemheat.nc",
        "nwp_extdat_chemheat_filename": "upatmo_gases_chemheat.nc",
    },
    "waves_nml": {
        "forc_file_prefix": NoDefault(),
    },
    "extpar_nml": {
        "extpar_filename": "<path>extpar_<gridfile>",
        "extpar_varnames_map_file": NotReadByDefault(""),
    },
}
