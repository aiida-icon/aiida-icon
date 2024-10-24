import aiida.orm
import f90nml

type NMLInput = aiida.orm.SinglefileData | f90nml.namelist.Namelist


def namelists_data(
    namelist: NMLInput,
) -> f90nml.namelist.Namelist:
    match namelist:
        case f90nml.namelist.Namelist():
            return namelist
        case aiida.orm.SinglefileData():
            return f90nml.reads(namelist.get_content())
        case _:
            raise ValueError
