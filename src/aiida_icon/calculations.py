from __future__ import annotations

import enum
import pathlib
import re
import typing

import f90nml
from aiida import engine, orm
from aiida.common import datastructures, folders
from aiida.parsers import parser

from aiida_icon.iconutils import modelnml

if typing.TYPE_CHECKING:
    from aiida.engine.processes.calcjobs import calcjob


class IconCalculation(engine.CalcJob):
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
        spec.output("latest_restart_file")
        spec.output_namespace("all_restart_files", dynamic=True)
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
            message="ICON did not create a restart file or directory.",
        )
        spec.exit_code(
            301,
            "ERROR_READING_STATUS_FILE",
            message="Could not read the finish.status file.",
        )
        spec.exit_code(
            302,
            "FAILED_CHECK_STATUS",
            message="The final status was not 'OK or RESTART', check the finish_status output.",
        )
        spec.exit_code(
            310,
            "ERROR_MISSING_RESTART_FILES",
            message="ICON was expected to produce a restart file but did not.",
        )

    def prepare_for_submission(self, folder: folders.Folder) -> datastructures.CalcInfo:
        model_namelist_data = f90nml.reads(self.inputs.model_namelist.get_content())
        master_namelist_data = f90nml.reads(self.inputs.master_namelist.get_content())

        for output_spec in model_namelist_data["output_nml"]:
            folder.get_subfolder(pathlib.Path(output_spec["output_filename"]).name, create=True)

        codeinfo = datastructures.CodeInfo()
        codeinfo.code_uuid = self.inputs.code.uuid

        calcinfo = datastructures.CalcInfo()
        calcinfo.codes_info = [codeinfo]
        calcinfo.remote_symlink_list = [
            (
                self.inputs.code.computer.uuid,
                self.inputs.dynamics_grid_file.get_remote_path(),
                model_namelist_data["grid_nml"]["dynamics_grid_filename"].strip(),
            ),
            (
                self.inputs.code.computer.uuid,
                self.inputs.ecrad_data.get_remote_path(),
                model_namelist_data["radiation_nml"]["ecrad_data_path"].strip(),
            ),
            (
                self.inputs.code.computer.uuid,
                self.inputs.rrtmg_sw.get_remote_path(),
                "rrtmg_sw.nc",
            ),
        ]
        calcinfo.remote_copy_list = [
            (
                self.inputs.code.computer.uuid,
                self.inputs.cloud_opt_props.get_remote_path(),
                "ECHAM6_CldOptProps.nc",
            ),
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
                master_namelist_data["master_model_nml"]["model_namelist_filename"].strip(),
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
        calcinfo.retrieve_list = [
            "finish.status",
            "nml.atmo.log",
            "output_schedule.txt",
        ]
        return calcinfo


class IconParser(parser.Parser):
    """Parser for raw Icon calculations."""

    class FinishStatus(enum.Enum):
        OK = enum.auto()
        RESTART = enum.auto()
        UNEXPECTED = enum.auto()
        ERR_READING_STATUS = enum.auto()
        ERR_MISSING_STATUS = enum.auto()

    def parse(self, **kwargs):  # noqa: ARG002  # kwargs must be there for superclass compatibility
        remote_folder = self.node.outputs.remote_folder
        remote_path = pathlib.Path(remote_folder.get_remote_path())
        finish_status = self.parse_finish_status()

        files = remote_folder.listdir()
        all_restarts_pattern = modelnml.restart_file_pattern()
        latest_restart_name = modelnml.latest_restart_multifile_link_name()

        all_restart_remotedatas = {}
        for file_name in files:
            if restart_match := re.match(all_restarts_pattern, file_name):
                all_restart_remotedatas[f"restart_{restart_match['timestamp']}"] = orm.RemoteData(
                    computer=self.node.computer,
                    remote_path=remote_path / file_name,
                )
            if file_name == latest_restart_name:
                self.out(
                    "latest_restart_file",
                    orm.RemoteData(computer=self.node.computer, remote_path=remote_path / file_name),
                )

        self.out("all_restart_files", all_restart_remotedatas)

        match finish_status:
            case self.FinishStatus.OK:
                return engine.ExitCode(0)
            case self.FinishStatus.RESTART:
                if self.node.latest_restart_file and all_restart_remotedatas:
                    return engine.ExitCode(0)
                return self.exit_codes.MISSING_RESTART_FILES
            case self.FinishStatus.UNEXPECTED:
                return self.exit_codes.FAILED_CHECK_STATUS
            case self.FinishStatus.ERR_READING_STATUS:
                return self.exit_codes.ERROR_READING_STATUS_FILE
            case self.FinishStatus.ERR_MISSING_STATUS:
                return self.exit_codes.ERROR_MISSING_OUTPUT_FILES

    def parse_finish_status(self) -> FinishStatus:
        if "finish.status" in self.retrieved.list_object_names():
            try:
                with self.retrieved.open("finish.status", "r") as status_file:
                    out_status = status_file.read().strip()
                    self.out("finish_status", orm.Str(out_status))
                    match out_status:
                        case "OK":
                            return self.FinishStatus.OK
                        case "RESTART":
                            return self.FinishStatus.RESTART
                        case _:
                            return self.FinishStatus.UNEXPECTED
            except OSError:
                return self.FinishStatus.ERR_READING_STATUS
        else:
            return self.FinishStatus.ERR_MISSING_STATUS
