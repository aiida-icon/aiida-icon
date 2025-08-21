from __future__ import annotations

import dataclasses
import pathlib
import tempfile
import typing

import f90nml
from aiida import orm
from aiida.common import exceptions as aiidaxc
from aiida.common import log as aiidalog
from aiida.transports import transport

from aiida_icon import exceptions

KeyT_contra = typing.TypeVar("KeyT_contra", contravariant=True)
ValT = typing.TypeVar("ValT")


class ReadMapProtocol(typing.Protocol[KeyT_contra, ValT]):
    def get(self, name: KeyT_contra, default: ValT) -> ValT: ...
    def __getitem__(self, name: KeyT_contra) -> ValT: ...
    def __contains__(self, name: KeyT_contra) -> bool: ...


class ReporterProtocol(typing.Protocol):
    def report(self, msg: str) -> None: ...


def collect_model_nml(namespace: ReadMapProtocol, *, download: bool = False) -> f90nml.Namelist:
    """Concatenate and parse all model namelist inputs into one f90nml.Namelist structure."""
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
                try:
                    with tempfile.NamedTemporaryFile() as tf:
                        result = nml.computer.get_transport().getfile(nml.get_remote_path(), tf.name)
                        result = f90nml.reads("\n".join([str(result), pathlib.Path(tf.name).read_text()]))
                except (aiidaxc.TransportTaskException, transport.TransportInternalError) as err:
                    raise exceptions.RemoteModelNamelistInaccessibleError from err
            case orm.RemoteData():
                pass  # no way to be helpful here
            case _:
                msg = f"Unexpected type for a model namelist input: {type(nml)}"
                raise TypeError(msg)
    return result


def make_remote_path_triplet(
    remote_path: orm.RemoteData, *, lookup_path: str | None = None, nml_data: f90nml.Namelist | None = None
) -> tuple[str, str, str]:
    """
    Make a local/remote_copy/link_list compatible triplet from a remote path.

    Optionally use the destination name / relative path stored in 'nml_data' at the given 'lookup_path',
    where 'lookup_path' is a dot-separated path through the nested namelist structure.
    """
    if not remote_path.computer:
        msg = "Can not make triplet from computerless RemoteData."
        raise ValueError(msg)
    comp = remote_path.computer.uuid
    src = remote_path.get_remote_path()
    tgt = pathlib.Path(src).name
    if lookup_path and nml_data:
        parts = lookup_path.split(".")
        for part in parts[:-1]:
            nml_data = nml_data.get(part, {})
        tgt = nml_data.get(parts[-1], tgt).strip()
    return (comp, src, tgt)


@dataclasses.dataclass
class ModelNamelistActions:
    """
    Indicates what needs to be added to local / remote copy list and which directories have to be created
    for setting up a model namelist file in the right place.
    """

    local_copy_list: list[tuple[str, str, str]] = dataclasses.field(default_factory=list)
    remote_copy_list: list[tuple[str, str, str]] = dataclasses.field(default_factory=list)
    create_dirs: list[pathlib.Path] = dataclasses.field(default_factory=list)


def make_model_actions(
    model_name: str,
    model_path: pathlib.Path,
    models_ns: ReadMapProtocol,
    reporter: ReporterProtocol = aiidalog.AIIDA_LOGGER,
) -> ModelNamelistActions:
    """
    Determine whether a model namelist input is passed correctly and how to prepare it for submission.

    Examples:

        >>> import io
        >>> from aiida.common.log import AIIDA_LOGGER
        >>> models_ns = {
        ...     "foo": orm.SinglefileData(io.StringIO("text")),
        ... }
        >>> actions = make_model_actions(
        ...     model_name="foo",
        ...     model_path=pathlib.Path("models/foo.nml"),
        ...     models_ns=models_ns,
        ...     reporter=AIIDA_LOGGER,
        ... )
        >>> len(actions.local_copy_list)  # should have one copy list triplet
        1
        >>> print([str(i) for i in actions.create_dirs])
        ['models']

        >>> actions = make_model_actions(
        ...     model_name="foo",
        ...     model_path=pathlib.Path("models/foo.nml"),
        ...     models_ns={},
        ...     reporter=AIIDA_LOGGER,
        ... )
        Traceback (most recent call last):
        aiida.common.exceptions.InputValidationError: Missing input for model 'foo'.
    """
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
                if not model_inp.computer:
                    msg = "RemoteData without computer can not be added to copy list"
                    raise aiidaxc.InternalError(msg)
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
        msg = f"Missing input for model '{model_name}'."
        raise aiidaxc.InputValidationError(msg)
    return result
