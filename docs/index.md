---
hide:
  - path
---

# AiiDA-ICON - Documentation

## About

aiida-icon is a plugin to the [AiiDA][aiida] scientific workflow manager.
It allows users of the [ICON][icon] weather & climate model to run
experiment workflows which:

- remember all the inputs and configurations they were run with
- do not require careful file-structure setup on the target machine before running
- can be shared and adapted by colleagues in a group
- are reproducible

## Quickstart

For users who do not want or need to learn how to leverage the full versatility of [AiiDA][aiida],
[Sirocco][sirocco] provides a declarative way to describe Climate & Weather workflows. This makes
usage similar to other, field-specific workflow managers, without sacrificing the benefits
of [AiiDA][aiida]. Many of the steps below will still apply if you want to use [Sirocco][sirocco],
except that installing [Sirocco][sirocco] will install aiida-icon as a dependency automatically.

Here's how to get started with a minimal setup:

### Install

1. Create and activate a python environment from which you will run your experiments. Conda, Virtualenvwrapper, venv etc are all fine ways to achieve that. In case you expect to be developing workflows and submission scripts, which you would like to be portable between machines, you should consider a version controlled project using a project manager like `uv`, `hatch` or `poetry`.

2. Run `pip install aiida-icon` to install aiida-icon, AiiDA and all their dependencies. In the case of a project manager like `hatch`, use `hatch add aiida-icon` or your project manager's equivalent.

### Setup AiiDA

The following is a summary of the [AiiDA Quick Install Guide](https://aiida.readthedocs.io/projects/aiida-core/en/stable/installation/guide_quick.html) and the [AiiDA How To Run External Codes](https://aiida.readthedocs.io/projects/aiida-core/en/stable/howto/run_codes.html).

1. Install and run `rabbitmq 3.8.5`, either as a system service or as a docker image.

2. Run `verdi presto` to create your AiiDA profile

3. Run `verdi computer setup` to create a record of the target (HPC) machine you will use. This is not necessary if you are planning to run [ICON][icon] on your local machine, as `verdi presto` has already created a record called `localhost` for your local machine. Here you will give that record a name, later referred to as `<computername>`.

4. Allow AiiDA to connect to your target machine.
   1. In general: run `verdi computer configure ssh <computername>` to allow AiiDA to connect to the target machine.
   2. For CSCS ALPS clusters: the recommended way is to
      1. Run `pip install aiida-firecrest`
      2. Set up firecrest connectivity to your target cluster using the [CSCS Knowledge Base Article](https://confluence.cscs.ch/display/KB/FirecREST+for+Alps)
      3. Run `verdi computer configure firecrest <computername>`
   3. Run `verdi computer test <computername>` to make sure a connection can be established.

<!-- prettier-ignore-start -->
!!! warning
    You have to choose in step 3 already when you set "Transport" and "Scheduler", whether you will use "ssh" or "firecrest" in step 4.
    Pick "core.ssh" for transport and combine it with any of the available schedulers to connect with ssh OR pick "firecrest" for **both**
    (firecrest is used for both file transport as well as communication with the scheduler).
<!-- prettier-ignore-end -->

5. Run `verdi code create icon` to set up an ICON executable on the computer you created in the previous step. Consult the AiiDA documentation for details.

### Get Productive

Now you are ready to either run bare-bones ICON jobs (checkout the `examples/` directory for inspiration), or to develop AiiDA workflows incorporating ICON jobs.

#### Run from all local namelist files

This is somewhat the best case for usability: AiiDA will remember all the parameters for you, as it stores the contents of the namelist files at the point of submitting the run.

Of course, this requires that your master namelist specifies to look for model namelists in the work directory of the job. AiiDA will not upload files to elsewhere. For example:

```
&master_nml
  model_base_dir = models   ! or ./models, may not be an absolute path
  ...
/
...
&master_model_nml
  model_name = "atm"
  model_namelist_filename = "<path>/atm.namelist"   ! referencing the relative "model_base_dir" as "<path>"
  model_type = 1
  ...
/
...
```

This will cause AiiDA-ICON to upload a copy of your local "atm.namelist" into the "models" sub directory of the work directory. This works for multiple model namelists too.

```python
#!verdi run
from aiida import orm
from aiida_icon.calculations import IconCalculation

code = orm.load_code("myicon@myhpc")
builder = IconCalculation.get_builder()
builder.code = code
builder.master_namelist = orm.SinglefileData("/path/to/my/master.nml")
builder.models.atm = orm.SinglefileData("/path/to/my/atm.namelist")
builder.submit() # or .run() if you have not set up rabbitmq for your AiiDA profile
```

In this case, AiiDA keeps a snapshot of the contents of all the model namelist files for later reference - freeing you up to do with the files themselves as you wish.

#### Run an ICON job from just a master namelist file

The absolute minimum requirement is that you have the contents of your master namelist file available
on the computer you submit from.

Assume you have one that looks as follows:

```
&master_nml
  model_base_dir = /homes/myuser/models
  ...
/
...
&master_model_nml
  model_name = "atm"
  model_namelist_filename = "<path>/atm.namelist"
  model_type = 1
  ...
/
...
```

This has to be in a file local to where you are running AiiDA.
And you have the appropriate files in the appropriate places on your remote machine.
You also have a code set up on your hpc system (named "myhpc" in your DB) and you named it "myicon".

You can submit the job with the following script:

```python
#!verdi run
from aiida import orm
from aiida_icon.calculations import IconCalculation

code = orm.load_code("myicon@myhpc")
builder = IconCalculation.get_builder()
builder.code = code
builder.master_namelist = orm.SinglefileData("/path/to/my/master.nml")
builder.submit() # or .run() if you have not set up rabbitmq for your AiiDA profile
```

Note that this will do two things with your master namelist file:

1. It will keep the contents in your AiiDA database, forever connected to this run. You can change the file safely later and still inspect what it looked like when you ran this.
2. It will upload a copy of it to the work directory of the job on your HPC machine (whether that be a remote one or your laptop), where it will also stay unchanged until cleaned up by you or by some file system policy.

This means you keep a record of the exact parameters used, even if you change the file. It also means you can use that same set of parameters in future runs, even if the file is gone from your file system.

#### Run ICON job with provenance

Using the same ICON job as above: you might want to consider tracking the model namelist files your run is using inside the AiiDA graph. This makes it convenient to later inspect or retrieve them, without opening up the master namelist file first.

```python
...

builder.master_namelist = orm.SinglefileData("/path/to/my/master.nml")
builder.models.atm = orm.RemoteData(code.computer, remote_path="/homes/myuser/models/atm.namelist")  # the 'remote_path' has to exactly match what the master namelist specifies
```

In this case, no additional files are moved, the `.models.atm` input is simply there to keep a record of what file path you used in the database. Looking back later, there is no way to even know if the file has been changed after this was run.

## Recipes for specific use cases

Find detailed instructions for specific known usecases [here](recipes.md)

[icon]: https://icon-model.org "ICON - Climate & Weather Model"
[aiida]: https://www.aiida.net "AiiDA - Workflow Manager"
[sirocco]: https://github.com/C2SM/Sirocco "Sirocco - dynamic Climate & Weather Workflows"
