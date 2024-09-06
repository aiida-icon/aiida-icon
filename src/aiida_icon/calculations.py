from __future__ import annotations

import pathlib
import re
import typing

import f90nml
from aiida import engine, orm
from aiida.common import datastructures, folders
from aiida.parsers import parser

if typing.TYPE_CHECKING:
    from aiida.engine.processes.calcjobs import calcjob


class Icon(engine.CalcJob):
    """AiiDA calculation to run ICON."""

    @classmethod
    def define(cls, spec: calcjob.CalcJobProcessSpec) -> None:  # type: ignore[override] # forced by aiida-core
        super().define(spec)
        spec.input("master_namelist", valid_type=orm.SinglefileData)
        spec.input("model_namelist", valid_type=orm.SinglefileData)
        spec.input("wrapper_script", valid_type=orm.SinglefileData, required=False)
        spec.input(
            "dynamics_grid_file",
            valid_type=orm.RemoteData,
        )
        spec.input("ecrad_data", valid_type=orm.RemoteData)
        spec.input("cloud_opt_props", valid_type=orm.RemoteData)
        spec.input("dmin_wetgrowth_lookup", valid_type=orm.RemoteData)
        spec.input("rrtmg_sw", valid_type=orm.RemoteData)
        spec.output("restart_file_dir")
        spec.output("restart_file_name")
        spec.output("finish_status")
        options = spec.inputs["metadata"]["options"]  # type: ignore[index] # guaranteed correct by aiida-core
        options["resources"].default = {  # type: ignore[index] # guaranteed correct by aiida-core
            "num_machines": 10,
            "num_mpiprocs_per_machine": 1,
            "num_cores_per_mpiproc": 2,
        }
        options["withmpi"].default = True  # type: ignore[index] # guaranteed correct by aiida-core
        options["parser_name"].default = "aiida_icon.icon"  # type: ignore[index] # guaranteed correct by aiida-core
        spec.exit_code(
            300,
            "ERROR_MISSING_OUTPUT_FILES",
            message="ICON did not create a restart file or directory!",
        )
        spec.exit_code(
            301,
            "ERROR_READING_STATUS_FILE",
            message="Could not read the finish.status file!",
        )
        spec.exit_code(
            302,
            "FAILED_CHECK_STATUS",
            message="The final status was not 'OK', check the finish_status output!",
        )

    def prepare_for_submission(self, folder: folders.Folder) -> datastructures.CalcInfo:
        model_namelist_data = f90nml.reads(self.inputs.model_namelist.get_content())

        for output_spec in model_namelist_data["output_nml"]:
            folder.get_subfolder(pathlib.Path(output_spec["output_filename"]).name, create=True)

        codeinfo = datastructures.CodeInfo()
        codeinfo.code_uuid = self.inputs.code.uuid

        calcinfo = datastructures.CalcInfo()
        calcinfo.codes_info = [codeinfo]
        calcinfo.remote_symlink_list = [
            (
                self.inputs.code.computer.uuid,
                dynamics_grid_path := self.inputs.dynamics_grid_file.get_remote_path(),
                pathlib.Path(dynamics_grid_path).name,
            ),
            (
                self.inputs.code.computer.uuid,
                self.inputs.ecrad_data.get_remote_path(),
                "ecrad_data",
            ),
            (
                self.inputs.code.computer.uuid,
                self.inputs.rrtmg_sw.get_remote_path(),
                "rrtmg_sw.nc",
            ),
        ]
        calcinfo.remote_copy_list = [
            (self.inputs.code.computer.uuid, self.inputs.cloud_opt_props.get_remote_path(), "ECHAM6_CldOptProps.nc"),
            (
                self.inputs.code.computer.uuid,
                self.inputs.dmin_wetgrowth_lookup.get_remote_path(),
                "dmin_wetgrowth_lookup.nc",
            ),
        ]

        calcinfo.local_copy_list = [
            (
                self.inputs.master_namelist.uuid,
                self.inputs.master_namelist.filename,
                "icon_master.namelist",
            ),
            (
                self.inputs.model_namelist.uuid,
                self.inputs.model_namelist.filename,
                "model.namelist",
            ),
        ]

        if self.inputs.wrapper_script:
            calcinfo.local_copy_list.append(
                (
                    self.inputs.wrapper_script.uuid,
                    self.inputs.wrapper_script.filename,
                    "run_icon.sh",
                )
            )
        calcinfo.retrieve_list = ["finish.status", "nml.atmo.log", "output_schedule.txt"]
        return calcinfo


class IconParser(parser.Parser):
    """Parser for raw Icon calculations."""

    def parse(self, **kwargs):  # noqa: ARG002  # kwargs must be there for superclass compatibility
        remote_folder = self.node.outputs.remote_folder

        files = remote_folder.listdir()
        restart_pattern = re.compile(r".*_restart_atm_\d{8}T.*\.nc")
        multirestart_pattern = re.compile(r"multifile_restart_atm_\d{8}T.*.mfr")

        for file_name in files:
            if re.match(restart_pattern, file_name) or re.match(multirestart_pattern, file_name):
                self.out("restart_file_name", orm.Str(file_name))
                self.out("restart_file_dir", self.node.outputs.remote_folder.clone())

        if "finish.status" in self.retrieved.list_object_names():
            try:
                with self.retrieved.open("finish.status", "r") as status_file:
                    out_status = status_file.read().strip()
                    self.out("finish_status", orm.Str(out_status))
                    if out_status == "OK":
                        return engine.ExitCode(0)
                    return self.exit_codes.FAILED_CHECK_STATUS
            except OSError:
                return self.exit_codes.ERROR_READING_STATUS_FILE
        else:
            return self.exit_codes.ERROR_MISSING_OUTPUT_FILES
