import dataclasses
import functools
import pathlib

import aiida
import aiida.common
import aiida.orm
import pytest

from aiida_icon.calculations import IconCalculation

pytest_plugins = ["aiida.tools.pytest_fixtures"]


@dataclasses.dataclass
class ParserCase:
    datapath: pathlib.Path
    exit_code: int
    required_output_links: list[str]
    disallowed_output_links: list[str]
    finish_status_value: str


PARSER_CASES = {
    "simple_icon_run": ("simple_icon_run", 0, ["finish_status"], [], "OK"),
    "restarts_present": (
        "restarts_present",
        0,
        ["finish_status", "latest_restart_file", "all_restart_files"],
        [],
        "RESTART",
    ),
    "restarts_missing": (
        "restarts_missing",
        304,
        ["finish_status"],
        ["latest_restart_file", "all_restart_files"],
        "RESTART",
    ),
}


@pytest.fixture(params=["simple_icon_run", "restarts_present", "restarts_missing"])
def case_name(request):
    return request.param


@pytest.fixture
def parser_case(case_name):
    case_name, *args = PARSER_CASES[case_name]
    return ParserCase(pathlib.Path(__file__).parent.absolute() / "data" / case_name, *args)


@dataclasses.dataclass
class BuildInputs:
    fake_icon: aiida.orm.CalcJobNode

    def __setattr__(self, name: str, value: aiida.orm.Data) -> None:
        if name == "fake_icon":
            super().__setattr__(name, value)
        else:
            self.fake_icon.base.links.add_incoming(
                source=value,
                link_type=aiida.common.LinkType.INPUT_CALC,
                link_label=name,
            )


@dataclasses.dataclass
class BuildOutputs:
    fake_icon: aiida.orm.CalcJobNode

    def __setattr__(self, name: str, value: aiida.orm.Data) -> None:
        if name == "fake_icon":
            super().__setattr__(name, value)
        else:
            value.base.links.add_incoming(
                link_type=aiida.common.LinkType.CREATE,
                source=self.fake_icon,
                link_label=name,
            )


class FakeIconBuilder:
    node: aiida.orm.CalcJobNode

    def __init__(self, computer: aiida.orm.Computer):
        self.node = aiida.orm.CalcJobNode(computer=computer, process_type="aiida.calculations:icon.icon")

    @property
    def inputs(self) -> BuildInputs:
        return BuildInputs(self.node)

    @property
    def outputs(self) -> BuildOutputs:
        return BuildOutputs(self.node)

    def build(self) -> aiida.orm.CalcJobNode:
        self.node.store_all()
        return self.node


@pytest.fixture
def icon_result(parser_case, aiida_computer_local):
    """Mockup a finished calculation for a given set of inputs and outputs."""
    datapath = parser_case.datapath
    computer = aiida_computer_local()
    make_remote = functools.partial(aiida.orm.RemoteData, computer=computer)
    builder = FakeIconBuilder(computer=computer)
    builder.inputs.master_namelist = aiida.orm.SinglefileData(datapath / "inputs" / "icon_master.namelist")
    builder.inputs.model_namelist = aiida.orm.SinglefileData(datapath / "inputs" / "model.namelist")
    builder.inputs.dynamics_grid_file = make_remote(
        remote_path=str(datapath.absolute() / "inputs" / "icon_grid_simple.nc")
    )
    builder.inputs.ecrad_data = make_remote(remote_path=str(datapath.absolute() / "inputs" / "ecrad_data"))
    builder.inputs.rrtmg_sw = make_remote(remote_path=str(datapath.absolute() / "inputs" / "rrtmg_sw.nc"))
    builder.inputs.cloud_opt_props = make_remote(
        remote_path=str(datapath.absolute() / "inputs" / "ECHAM6_CldOptProps.nc")
    )
    builder.inputs.dmin_wetgrowth_lookup = make_remote(
        remote_path=str(datapath.absolute() / "inputs" / "dmin_wetgrowth_lookup.nc")
    )
    node = builder.build()
    builder.outputs.remote_folder = make_remote(str(datapath.absolute() / "outputs")).store()

    retrieved = aiida.orm.FolderData()
    retrieved_files = [
        "_aiidasubmit.sh",
        "_scheduler-stderr.txt",
        "_scheduler-stdout.txt",
        "finish.status",
    ]
    for filename in retrieved_files:
        retrieved.put_object_from_file(str(datapath.absolute() / "outputs" / filename), filename)
    builder.outputs.retrieved = retrieved.store()

    return node


@pytest.fixture
def icon_calc(aiida_computer_local, aiida_code_installed):
    """Create an IconCalculation which is ready to call .prepare_for_submission()."""
    code = aiida_code_installed(default_calc_job_plugin="icon.icon", computer=aiida_computer_local())
    datapath = pathlib.Path(__file__).parent.absolute() / "data" / "simple_icon_run"
    builder = code.get_builder()
    make_remote = functools.partial(aiida.orm.RemoteData, computer=code.computer)
    builder.master_namelist = aiida.orm.SinglefileData(datapath / "inputs" / "icon_master.namelist")
    builder.model_namelist = aiida.orm.SinglefileData(datapath / "inputs" / "model.namelist")
    builder.dynamics_grid_file = make_remote(remote_path=str(datapath.absolute() / "inputs" / "icon_grid_simple.nc"))
    builder.ecrad_data = make_remote(remote_path=str(datapath.absolute() / "inputs" / "ecrad_data"))
    builder.rrtmg_sw = make_remote(remote_path=str(datapath.absolute() / "inputs" / "rrtmg_sw.nc"))
    builder.cloud_opt_props = make_remote(remote_path=str(datapath.absolute() / "inputs" / "ECHAM6_CldOptProps.nc"))
    builder.dmin_wetgrowth_lookup = make_remote(
        remote_path=str(datapath.absolute() / "inputs" / "dmin_wetgrowth_lookup.nc")
    )
    return IconCalculation(dict(builder))
