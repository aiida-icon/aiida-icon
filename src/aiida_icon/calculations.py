from __future__ import annotations

import dataclasses
import enum
import pathlib
import re
import typing

import f90nml
from aiida import engine, orm
from aiida.common import datastructures, folders
from aiida.parsers import parser

from aiida_icon import exceptions
from aiida_icon.iconutils import masternml, modelnml

if typing.TYPE_CHECKING:
    from aiida.engine.processes.calcjobs import calcjob


class IconCalculation(engine.CalcJob):
    """AiiDA calculation to run ICON."""

    @classmethod
    def define(cls, spec: calcjob.CalcJobProcessSpec) -> None:  # type: ignore[override] # forced by aiida-core
        super().define(spec)
        spec.input("master_namelist", valid_type=orm.SinglefileData)
        spec.input("model_namelist", valid_type=orm.SinglefileData)
        spec.input("restart_file", valid_type=orm.RemoteData, required=False)
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
        options["parser_name"].default = "icon.icon"  # type: ignore[index] # guaranteed correct by aiida-core
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
        # deprecated, replaced by 304: PARTIALLY_PARSED + log messages
        spec.exit_code(
            302,
            "FAILED_CHECK_STATUS",
            message="The final status was not 'OK or RESTART', check the finish_status output.",
        )
        # deprecated, replaced by 304: PARTIALLY_PARSED + log messages
        spec.exit_code(
            303,
            "UNSUPPORTED_FEATURE",
            message="Could not fully parse due to an unsupported feature, please check the log.",
        )
        spec.exit_code(
            304,
            "PARTIALLY_PARSED",
            message="Some outputs might be missing, check the log for explanations.",
        )
        # deprecated, replaced by 304: PARTIALLY_PARSED + log messages
        spec.exit_code(
            310,
            "ERROR_MISSING_RESTART_FILES",
            message="ICON was expected to produce a restart file but did not.",
        )

    def prepare_for_submission(self, folder: folders.Folder) -> datastructures.CalcInfo:
        model_namelist_data = f90nml.reads(self.inputs.model_namelist.get_content())
        master_namelist_data = f90nml.reads(self.inputs.master_namelist.get_content())

        for output_folder in modelnml.read_output_stream_paths(model_namelist_data):
            folder.get_subfolder(output_folder, create=True)

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
        if "restart_file" in self.inputs:
            calcinfo.remote_symlink_list.append(
                (
                    self.inputs.code.computer.uuid,
                    self.inputs.restart_file.get_remote_path(),
                    modelnml.read_latest_restart_file_link_name(model_namelist_data),
                )
            )
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

        if "wrapper_script" in self.inputs:
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


class FinishStatus(enum.Enum):
    OK = enum.auto()
    RESTART = enum.auto()
    UNEXPECTED = enum.auto()
    ERR_READING_STATUS = enum.auto()
    ERR_MISSING_STATUS = enum.auto()


class RestartStatus(enum.Enum):
    OK = enum.auto()
    MISSING = enum.auto()
    ERROR = enum.auto()


@dataclasses.dataclass
class FinishStatusResult:
    status: FinishStatus
    message: orm.Str | None = None


@dataclasses.dataclass
class RestartResult:
    status: RestartStatus
    all_restarts: dict[str, orm.RemoteData] = dataclasses.field(default_factory=dict)
    latest_restart: orm.RemoteData | None = None


class IconParser(parser.Parser):
    """Parser for raw Icon calculations."""

    def parse(self, **kwargs):  # noqa: ARG002  # kwargs must be there for superclass compatibility
        finish_status = self.parse_finish_status()
        if finish_status.message:
            self.out("finish_status", finish_status.message)

        restart_indicated = finish_status is FinishStatus.RESTART or masternml.read_lrestart_write_last(
            self.node.inputs.master_namelist
        )
        restarts = self.parse_restart_files(restart_indicated=restart_indicated)
        if restarts.all_restarts:
            self.out("all_restart_files", restarts.all_restarts)
        if restarts.latest_restart:
            self.out("latest_restart_file", restarts.latest_restart)

        match finish_status.status:
            case FinishStatus.OK:
                pass
            case FinishStatus.RESTART:
                if restarts.status is not RestartStatus.OK:
                    return self.exit_codes.PARTIALLY_PARSED
            case FinishStatus.UNEXPECTED:
                return self.exit_codes.PARTIALLY_PARSED
            case FinishStatus.ERR_READING_STATUS:
                return self.exit_codes.ERROR_READING_STATUS_FILE
            case FinishStatus.ERR_MISSING_STATUS:
                return self.exit_codes.ERROR_MISSING_OUTPUT_FILES

        return engine.ExitCode(0)

    def parse_finish_status(self) -> FinishStatusResult:
        result = FinishStatusResult(status=FinishStatus.ERR_MISSING_STATUS, message=None)
        if "finish.status" in self.retrieved.list_object_names():
            try:
                with self.retrieved.open("finish.status", "r") as status_file:
                    out_status = status_file.read().strip()
                    result.message = orm.Str(out_status)
                    match out_status:
                        case "OK":
                            result.status = FinishStatus.OK
                        case "RESTART":
                            result.status = FinishStatus.RESTART
                        case _:
                            result.status = FinishStatus.UNEXPECTED
                            self.logger.info("The 'finish.status' file contained an unexpected value.")
            except OSError as err:
                result.status = FinishStatus.ERR_READING_STATUS
                self.logger.warning(str(err))
                self.logger.warning("The 'finish.status' file was found but could not be read.")
        else:
            self.logger.warning("The 'finish.status' file could not be found in the output.")

        return result

    def parse_restart_files(self, *, restart_indicated: bool) -> RestartResult:
        remote_folder = self.node.outputs.remote_folder
        remote_path = pathlib.Path(remote_folder.get_remote_path())

        files = remote_folder.listdir()
        result = RestartResult(status=RestartStatus.MISSING)
        try:
            all_restarts_pattern = modelnml.read_restart_file_pattern(self.node.inputs.model_namelist)
            latest_restart_name = modelnml.read_latest_restart_file_link_name(self.node.inputs.model_namelist)
        except exceptions.SinglefileRestartNotImplementedError:
            self.logger.info("Can not parse restart file names, singlefile mode is not supported.")
            if restart_indicated:
                result.status = RestartStatus.ERROR

        for file_name in files:
            if restart_match := re.match(all_restarts_pattern, file_name):
                result.all_restarts[f"restart_{restart_match['timestamp']}"] = orm.RemoteData(
                    computer=self.node.computer,
                    remote_path=str(remote_path / file_name),
                )
            if file_name == latest_restart_name:
                result.latest_restart = orm.RemoteData(
                    computer=self.node.computer,
                    remote_path=str(remote_path / file_name),
                )

        if result.all_restarts and result.latest_restart:
            result.status = RestartStatus.OK
        else:
            self.logger.info("Could not find a valid set of restart files.")

        return result
