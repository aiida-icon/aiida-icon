# AiiDA-ICON Recipes

## Run ICON via a wrapper script

<!-- prettier-ignore-start -->
!!! warning
    None of the following will work if you opt out of running with MPI.
<!-- prettier-ignore-end -->

On some HPC facilities it is common to run ICON using the following pattern

```bash
mpirun --<options> wrapper_script.sh </path/to/icon/binary>
```

```bash
srun --<options> wrapper_script.sh </path/to/icon/binary>
```

etc, where the job of the `wrapper_script.sh` is to prepare environment variables
and other things specific to the machine being used to obtain the best possible performance.

Here is an example how to do this with AiiDA-ICON:

```python
from aiida import orm
from aiida_icon.calculations import IconCalculation

builder = IconCalculation.get_builder()
builder.wrapper_script = orm.SinglefileData("/path/to/my/wrapper_script.sh")
...
```

Currently you have to have a copy of this wrapper script locally, which AiiDA will upload for you.
Alternatively you can create a `SinglefileData` instance from a string with the script contents.

This is so that the AiiDA graph after the fact can record exactly how you ran ICON at the time.

<!-- prettier-ignore-start -->
!!! note
    Adding the `.wrapper_script` input will automatically add a line to the `builder.metadata.options.prepend_text`. Take care not to delete it or you will get an error at run time that the wrapper script is not executable.

!!! note
    Adding the `.wrapper_script` input will automatically add the wrapper script to `builder.metadata.options.mpirun_extra_params`. Take care to keep it as the last entry of that list (unless it takes additional arguments itself, those have to go afterwards).
<!-- prettier-ignore-end -->

Since this affects also the prepend text as well as the parameters sent to the "mpirun equivalent" on your system, here is a continuation of the above example that shows how to manipulate those in the presence of a wrapper script.

```python
builder.wrapper_script = orm.SinglefileData("/path/to/my/wrapper_script.sh")
...
options = builder.metadata.options
# load a module before making the wrapper script executable
# and print a message afterwards
options.prepend_text = f"module load somemodule\n{options.prepend_text}\necho 'everything ready'"
# add an mpirun/srun/etc option
options.mpirun_extra_params.insert(-1, "--myoption")
```

<!-- prettier-ignore-start -->
!!! note
    AiiDA-ICON will rename the uploaded copy of your wrapper script to `run_icon.sh` for simplicity and
universal readability.
<!-- prettier-ignore-end -->
