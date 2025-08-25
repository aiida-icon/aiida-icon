"""
Ensure database nodes created by the first experimentally used version can still be loaded
and inspected properly with the current version.
"""

from aiida import orm
from aiida.tools.archive import imports as archive_imports


def test_v0_4_import(datapath, caplog):
    _ = archive_imports.import_archive(datapath / "archives" / "icon_calc_v0.4.aiida")
    n_import_log_lines = len(caplog.record_tuples)
    testee = orm.load_node(label="icon.icon_v0.4")
    exit_code = testee.get_parser_class()(testee).parse()
    assert len(caplog.record_tuples) == n_import_log_lines  # check that loading the node does not log a warning
    assert testee.inputs.model_namelist  # check that the deprecated model_namelist input is accessible
    assert exit_code.status == 0
