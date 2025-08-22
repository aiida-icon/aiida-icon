import pathlib
import re
import textwrap

import f90nml
import pytest
from aiida import orm

from aiida_icon import calcutils


@pytest.fixture
def model_bar():
    return orm.SinglefileData.from_string(
        textwrap.dedent(
            """
        &bar
         b=1
        /
        """
        )
    )


@pytest.fixture
def model_foo():
    return orm.SinglefileData.from_string(
        textwrap.dedent(
            """
        &foo
         a=1
        /
        """
        )
    )


def test_collect_model_nml_modern(model_foo, model_bar):
    foo = model_foo
    bar = model_bar
    testee = calcutils.collect_model_nml({"models": {"foo": foo, "bar": bar}}, download=True)
    assert testee["foo"]["a"] == 1
    assert testee["bar"]["b"] == 1


def test_collect_model_nml_old(model_foo, model_bar):
    foo = model_foo
    bar = model_bar
    testee = calcutils.collect_model_nml({"model_namelist": foo, "models": {"bar": bar}}, download=True)
    assert testee["foo"]["a"] == 1
    assert testee["bar"]["b"] == 1


def test_make_remote_path_triplet(aiida_computer_local):
    comp = aiida_computer_local()
    some_file = orm.RemoteData(computer=comp, remote_path="/some/file")
    testee = calcutils.make_remote_path_triplet(some_file)
    assert testee[2] == "file"


def test_make_remote_path_triplet_with_lookup(aiida_computer_local):
    comp = aiida_computer_local()
    some_file = orm.RemoteData(computer=comp, remote_path="/some/file")
    testee = calcutils.make_remote_path_triplet(
        some_file,
        lookup_path="foo.bar",
        nml_data=f90nml.Namelist({"foo": {"bar": "   newname"}}),
    )
    assert testee[2] == "newname"


def test_make_model_actions_remote_copy(caplog, aiida_computer_local):
    comp = aiida_computer_local()
    testee = calcutils.make_model_actions(
        model_name="foo",
        model_path=pathlib.Path("models/foo.nml"),
        models_ns={"foo": orm.RemoteData(computer=comp, remote_path="/some/file")},
    )
    assert testee.local_copy_list == []
    assert testee.remote_copy_list[0][1] == "/some/file"
    assert testee.remote_copy_list[0][2] == "models/foo.nml"
    assert testee.create_dirs == [pathlib.Path("models")]
    assert caplog.record_tuples == []


def test_make_model_actions_remote_nocopy(caplog, aiida_computer_local):
    comp = aiida_computer_local()
    testee = calcutils.make_model_actions(
        model_name="foo",
        model_path=pathlib.Path("/models/foo.nml"),
        models_ns={"foo": orm.RemoteData(computer=comp, remote_path="/models/foo.nml")},
    )
    assert testee.local_copy_list == []
    assert testee.remote_copy_list == []
    assert testee.create_dirs == []
    assert caplog.record_tuples == []


def test_make_model_actions_remote_fail(caplog, aiida_computer_local):
    comp = aiida_computer_local()
    testee = calcutils.make_model_actions(
        model_name="foo",
        model_path=pathlib.Path("/models/foo.nml"),
        models_ns={"foo": orm.RemoteData(computer=comp, remote_path="/other/foo.nml")},
    )
    assert testee.local_copy_list == []
    assert testee.remote_copy_list == []
    assert testee.create_dirs == []
    assert re.search(
        r"Warning: .* /other/foo.nml .* does not match .* \(/models/foo.nml\)",
        caplog.record_tuples[0][2],
    )


def test_make_model_actions_local_fail(caplog, model_foo):
    testee = calcutils.make_model_actions(
        model_name="foo",
        model_path=pathlib.Path("/models/foo.nml"),
        models_ns={"foo": model_foo},
    )
    assert testee.local_copy_list == []
    assert testee.remote_copy_list == []
    assert testee.create_dirs == []
    assert re.search(r"Warning: Local file input .* ignored", caplog.record_tuples[0][2])


def test_make_model_actions_remote_noinput(caplog, datapath):
    testee = calcutils.make_model_actions(
        model_name="foo",
        model_path=pathlib.Path("/models/foo.nml"),
        models_ns={},
    )
    assert testee.local_copy_list == []
    assert testee.remote_copy_list == []
    assert testee.create_dirs == []
    assert re.search(
        r"Warning: Model namelist .* not tracked for provenance",
        caplog.record_tuples[0][2],
    )
