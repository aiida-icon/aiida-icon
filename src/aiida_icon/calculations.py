from __future__ import annotations

import pathlib
import re

from aiida import engine, orm
from aiida.common import datastructures, folders
from aiida.engine.processes.calcjobs import calcjob
from aiida.parsers import parser


class Icon(engine.CalcJob):
    """AiiDA calculation to run ICON."""

    @classmethod
    def define(cls, spec: calcjob.CalcJobProcessSpec) -> None:
        super().define(spec)
        spec.input("expid", valid_type=orm.Str, serializer=orm.to_aiida_type)
        spec.input(
            "ifs2icon_filename", valid_type=orm.Str, serializer=orm.to_aiida_type
        )
        spec.input(
            "gcm_converted", valid_type=orm.RemoteData, help="Converted GCM data."
        )
        spec.input(
            "boundary_data",
            valid_type=orm.RemoteData,
            help="Base directory for boundary data.",
        )
        spec.input(
            "inidata",
            valid_type=orm.RemoteData,
            help="Initial files.",
        )
        spec.input("ini_basedir", valid_type=orm.RemoteData)
        spec.input(
            "restart_file_dir",
            required=False,
            valid_type=orm.RemoteData,
            help="Remote dir containing the restart file.",
        )
        spec.input(
            "restart_file_name",
            required=False,
            valid_type=orm.Str,
            serializer=orm.to_aiida_type,
            help="Name of the restart file (or path relative to `restart_file_dir`).",
        )
        spec.input("master_namelist", valid_type=orm.SinglefileData)
        spec.input("model_namelist", valid_type=orm.SinglefileData)
        spec.input(
            "lam_grid_relpath",
            valid_type=orm.Str,
            serializer=orm.to_aiida_type,
            help="Relative to ini_basedir",
        )
        spec.input(
            "parent_grid_relpath",
            valid_type=orm.Str,
            serializer=orm.to_aiida_type,
            help="Relative to ini_basedir",
        )
        spec.input(
            "extpar_relpath",
            valid_type=orm.Str,
            serializer=orm.to_aiida_type,
            help="Relative to ini_basedir",
        )
        spec.input(
            "ghg_file_relpath",
            valid_type=orm.Str,
            serializer=orm.to_aiida_type,
            help="Relative to ini_basedir",
        )
        spec.input("ecraddir", valid_type=orm.RemoteData)
        spec.output("restart_file_dir")
        spec.output("restart_file_name")
        options = spec.inputs["metadata"]["options"]
        options["resources"].default = {
            "num_machines": 10,
            "num_mpiprocs_per_machine": 1,
            "num_cores_per_mpiproc": 2,
        }
        options["withmpi"].default = True
        options["mpirun_extra_params"].default = [
            "--ntasks-per-node",
            "1",
            "--hint=nomultithread",
            "--cpus-per-task",
            "1",
        ]
        options["parser_name"].default = "c2sm.spice_raw_icon"
        options["environment_variables"].default = {
            "GRAN_ICON": "core",
            #      "OMP_NUM_THREADS": 1,
            #      "ICON_THREADS": 1,
            #      "OMP_SCHEDULE": "static,12",
            #      "OMP_DYNAMIC": '"false"',
            #      "OMP_STACKSIZE": "200M",
            #      "NUM_THREAD_ICON": 1,
            #      "NUM_IO_PROCS": 1,
        }
        spec.exit_code(
            300,
            "ERROR_MISSING_OUTPUT_FILES",
            message="ICON did not create a restart file or directory!",
        )

    def prepare_for_submission(self, folder: folders.Folder) -> datastructures.CalcInfo:
        for outnum in range(1, 11):
            folder.get_subfolder(f"out{outnum:02}", create=True)

        codeinfo = datastructures.CodeInfo()
        codeinfo.code_uuid = self.inputs.code.uuid

        ini_basedir_path = pathlib.Path(self.inputs.ini_basedir.get_remote_path())
        inidata_path = pathlib.Path(self.inputs.inidata.get_remote_path())

        calcinfo = datastructures.CalcInfo()
        calcinfo.codes_info = [codeinfo]
        calcinfo.remote_symlink_list = [
            (
                self.inputs.code.computer.uuid,
                self.inputs.gcm_converted.get_remote_path(),
                "gcm_converted",
            ),
            (
                self.inputs.code.computer.uuid,
                self.inputs.boundary_data.get_remote_path(),
                "boundary_data",
            ),
            (
                self.inputs.code.computer.uuid,
                parent_grid_path := str(
                    ini_basedir_path / self.inputs.parent_grid_relpath.value
                ),
                pathlib.Path(parent_grid_path).name,
            ),
            (
                self.inputs.code.computer.uuid,
                lam_grid_path := str(
                    ini_basedir_path / self.inputs.lam_grid_relpath.value
                ),
                pathlib.Path(lam_grid_path).name,
            ),
            (
                self.inputs.code.computer.uuid,
                extpar_path := str(ini_basedir_path / self.inputs.extpar_relpath.value),
                pathlib.Path(extpar_path).name,
            ),
            (
                self.inputs.code.computer.uuid,
                str(
                    latbc_path := pathlib.Path(
                        self.inputs.ini_basedir.get_remote_path()
                    )
                    / "dict.latbc"
                ),
                latbc_path.name,
            ),
            (
                self.inputs.code.computer.uuid,
                ecraddir_path := self.inputs.ecraddir.get_remote_path(),
                pathlib.Path(ecraddir_path).name,
            ),
            (
                self.inputs.code.computer.uuid,
                str(inidata_path / self.inputs.ifs2icon_filename.value),
                self.inputs.ifs2icon_filename.value,
            ),
        ]
        if "restart_file_dir" in self.inputs:
            restart_path = (
                pathlib.Path(self.inputs.restart_file_dir.get_remote_path())
                / self.inputs.restart_file_name.value
            )
            calcinfo.remote_symlink_list += [
                (
                    self.inputs.code.computer.uuid,
                    str(restart_path),
                    "multifile_restart_atm.mfr"
                    if self.inputs.restart_file_name.value.startswith("multifile")
                    else "restart_atm_DOM01.nc",
                )
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
                f"NAMELIST_{self.inputs.expid.value}",
            ),
        ]
        return calcinfo


class IconParser(parser.Parser):
    """Parser for raw Icon calculations."""

    def parse(self, **kwargs):
        remote_folder = self.node.outputs.remote_folder

        files = remote_folder.listdir()
        restart_pattern = re.compile(r".*_restart_atm_\d{8}T.*\.nc")
        multirestart_pattern = re.compile(r"multifile_restart_atm_\d{8}T.*.mfr")
        for file_name in files:
            if re.match(restart_pattern, file_name) or re.match(
                multirestart_pattern, file_name
            ):
                self.out("restart_file_name", orm.Str(file_name))
                self.out("restart_file_dir", self.node.outputs.remote_folder.clone())
                return engine.ExitCode(0)
        return self.exit_codes.ERROR_MISSING_OUTPUT_FILES
