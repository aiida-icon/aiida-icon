from __future__ import annotations

import dataclasses
import pathlib
import tempfile
import typing

import f90nml
from aiida import orm
from aiida.common import exceptions as aiidaxc

if typing.TYPE_CHECKING:
    from aiida import engine
    from aiida.engine.processes import ports
    from plumpy import utils as putils


def collect_model_nml(
    namespace: ports.PortNamespace | putils.AttributesFrozendict, *, download: bool = False
) -> f90nml.Namelist:
    result = f90nml.Namelist()
    # TODO: this is for the old way of passing a single model nml,
    # should go away at some point
    if "model_namelist" in namespace:
        result = f90nml.reads(
            str(result) + "\n" + typing.cast(orm.SinglefileData, namespace["model_namelist"]).get_content(mode="r")
        )
    for nml in namespace.get("models", {}).values():
        match nml:
            case orm.SinglefileData():
                result = f90nml.reads("\n".join([str(result), nml.get_content(mode="r")]))
            case orm.RemoteData() if download and nml.computer:
                with tempfile.NamedTemporaryFile() as tf:
                    result = nml.computer.get_transport().getfile(nml.get_remote_path(), tf.name)
                    result = f90nml.reads("\n".join([str(result), pathlib.Path(tf.name).read_text()]))
            case orm.RemoteData():
                pass  # no way to be helpful here
            case _:
                msg = f"Unexpected type for a model namelist input: {type(nml)}"
                raise TypeError(msg)
    return result


def make_remote_path_triplet(
    remote_path: orm.RemoteData, *, lookup_path: str | None = None, nml_data: f90nml.Namelist
) -> tuple[str, str, str]:
    if not remote_path.computer:
        msg = "Can not make triplet from computerless RemoteData."
        raise ValueError(msg)
    comp = remote_path.computer.uuid
    src = remote_path.get_remote_path()
    tgt = pathlib.Path(src).name
    if lookup_path:
        parts = lookup_path.split(".")
        for part in parts[:-1]:
            nml_data = nml_data.get(part, {})
        tgt = nml_data.get(parts[-1], tgt)
    return (comp, src, tgt)


@dataclasses.dataclass
class ModelNamelistActions:
    local_copy_list: list[tuple[str, str, str]] = dataclasses.field(default_factory=list)
    remote_copy_list: list[tuple[str, str, str]] = dataclasses.field(default_factory=list)
    create_dirs: list[pathlib.Path] = dataclasses.field(default_factory=list)


def make_model_actions(
    model_name: str, model_path: pathlib.Path, models_ns: ports.PortNamespace, reporter: engine.CalcJob
) -> ModelNamelistActions:
    result = ModelNamelistActions()
    if not model_path.is_absolute() and model_path.parent != pathlib.Path("."):
        result.create_dirs.append(model_path.parent)
    if model_name in models_ns:
        match model_inp := models_ns[model_name]:
            case orm.RemoteData() if model_path.is_absolute():
                if model_path != pathlib.Path(model_inp.get_remote_path()):
                    reporter.report(
                        f"Warning: Remote path {model_inp.get_remote_path()} for "
                        f"model input '{model_name}' does not match absolute path "
                        f"given in master namelists ({model_path}). Using the path in master namelists."
                    )
            case orm.RemoteData():
                result.remote_copy_list.append((model_inp.computer.uuid, model_inp.get_remote_path(), str(model_path)))
            case orm.SinglefileData() if model_path.is_absolute():
                reporter.report(
                    f"Warning: Local file input for model '{model_name}' ignored, "
                    "because master namelist gives an absolute remote path for it "
                    "(AiiDA will not write files outside the run directory)."
                )
            case orm.SinglefileData():
                result.local_copy_list.append((model_inp.uuid, model_inp.filename, str(model_path)))
    elif model_path.is_absolute():
        reporter.report(f"Warning: Model namelist for model '{model_name}' is not tracked for provenance.")
    else:
        reporter.report(f"Error: Model namelist input for model '{model_name}' is missing!")
        msg = f"Missing input for model '{model_name}'"
        raise aiidaxc.InputValidationError(msg)
    return result
