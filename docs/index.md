---
hide:
  - navigation
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

### Get Productive

1. Now you are ready to either run bare-bones ICON jobs (checkout the `examples/` directory for inspiration), or to develop AiiDA workflows incorporating ICON jobs.

[icon]: https://icon-model.org "ICON - Climate & Weather Model"
[aiida]: https://www.aiida.net "AiiDA - Workflow Manager"
[sirocco]: https://github.com/C2SM/Sirocco "Sirocco - dynamic Climate & Weather Workflows"
