from aiida import engine, orm
from aiida.engine.processes.calcjobs import calcjob

from aiida_icon import builder


class GenericIconCalculation(engine.CalcJob):
    @classmethod
    def get_builder(cls) -> builder.IconCalculationBuilder:
        return builder.IconCalculationBuilder(cls)

    @classmethod
    def define(cls, spec: calcjob.CalcJobProcessSpec) -> None:  # type: ignore[override] # forced by aiida-core
        super().define(spec)
        spec.input("master_namelist", valid_type=orm.SinglefileData, required=True)
        spec.input_namespace("models", valid_type=orm.SinglefileData, required=False)
        spec.input_namespace("upload", valid_type=orm.SinglefileData, required=False)
        spec.input_namespace("onsite", valid_type=orm.RemoteData, required=False)
        spec.input("wrapper_script", valid_type=orm.SinglefileData, required=False)
        spec.input("setup_env", valid_type=orm.SinglefileData, required=False)
        spec.output("restart", valid_type=orm.Str)
        spec.output_namespace("checkpoints", valid_type=orm.Str, dynamic=True)
        spec.output_namespace("output_streams", dynamic=True)
