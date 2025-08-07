from aiida_icon import builder, calculations, tools


def test_double_uenv(aiida_code_installed, aiida_computer_local):
    code = aiida_code_installed(default_calc_job_plugin="icon.icon", computer=aiida_computer_local())
    code.store()
    tools.code_set_uenv(code, uenv=tools.Uenv(name="foo", view="bar"))
    ibuilder = builder.IconCalculationBuilder(calculations.IconCalculation)
    ibuilder.code = code
    ibuilder.set_uenv(uenv_name="foo", view="bar", overwrite=False)
    assert ibuilder.metadata.options.custom_scheduler_commands == "#SBATCH --uenv=foo --view=bar"
