"""Example script demonstrating how to query for namelist parameters in AiiDA.

This script shows how to find IconCalculation nodes based on specific
namelist parameter values stored in the SinglefileData attributes.
"""

from aiida import load_profile, orm
from aiida.orm import QueryBuilder, SinglefileData
from aiida_icon.calculations import IconCalculation

load_profile()

from aiida import orm, load_profile
from aiida.orm import QueryBuilder

from aiida_icon.calculations import IconCalculation

load_profile()


def query_by_model_namelist():
    """Query by model namelist parameters (e.g., atmosphere model settings).

    Note: Model namelists are stored separately by their key (e.g., 'atm', 'oce').
    Access them via extras.models.<model_key>.<namelist_section>.<parameter>
    """
    qb = QueryBuilder()
    qb.append(
        IconCalculation,
        filters={
            "extras.models.atm.parallel_nml.nproma": {"<": 100},
        },
        project=["uuid", "ctime"],
    )

    results = qb.all()
    print(f"Found {len(results)} calculations with atm nproma < 100")
    return results


def find_icon_calculations_by_model_namelist_param(
    section: str,
    parameter: str,
    value,
) -> list[IconCalculation]:
    """Find IconCalculations where a model namelist parameter has a specific value.

    Args:
        section: The namelist section (e.g., 'run_nml', 'nwp_phy_nml')
        parameter: The parameter name within the section
        value: The expected value

    Returns:
        List of IconCalculation nodes matching the criteria
    """
    qb = QueryBuilder()
    qb.append(
        IconCalculation,
        tag="calc",
        project=["*"],
    )
    qb.append(
        SinglefileData,
        with_outgoing="calc",  # SinglefileData is input to IconCalculation
        edge_filters={"label": {"like": "models__%"}},  # models.atm, models.oce, etc.
        filters={
            f"attributes.namelist.{section}.{parameter}": value,
        },
        tag="model_nml",
    )

    return [row[0] for row in qb.all()]


def find_icon_calculations_by_master_namelist_param(
    section: str,
    parameter: str,
    value,
) -> list[IconCalculation]:
    """Find IconCalculations where a master namelist parameter has a specific value.

    Args:
        section: The namelist section (e.g., 'master_nml', 'time_nml')
        parameter: The parameter name within the section
        value: The expected value

    Returns:
        List of IconCalculation nodes matching the criteria
    """
    qb = QueryBuilder()
    qb.append(
        IconCalculation,
        tag="calc",
        project=["*"],
    )
    qb.append(
        SinglefileData,
        with_outgoing="calc",
        edge_filters={"label": "master_namelist"},
        filters={
            f"attributes.namelist.{section}.{parameter}": value,
        },
        tag="master_nml",
    )

    return [row[0] for row in qb.all()]


def find_workflows_by_model_namelist_param(
    section: str,
    parameter: str,
    value,
) -> list[orm.WorkChainNode]:
    """Find top-level WorkGraph workflows containing IconCalculations with specific namelist params.

    Args:
        section: The namelist section
        parameter: The parameter name
        value: The expected value

    Returns:
        List of top-level WorkGraph workflows
    """
    qb = QueryBuilder()
    # Start from the top-level workflow (no caller)
    qb.append(
        orm.WorkChainNode,
        filters={"attributes.process_label": {"like": "WorkGraph<%"}},
        tag="workflow",
        project=["*"],
    )
    # Find IconCalculations called by (descendant of) the workflow
    qb.append(
        IconCalculation,
        with_ancestors="workflow",
        tag="calc",
    )
    # Filter by model namelist parameter
    qb.append(
        SinglefileData,
        with_outgoing="calc",
        edge_filters={"label": {"like": "models__%"}},
        filters={
            f"attributes.namelist.{section}.{parameter}": value,
        },
    )

    # Get unique workflows
    workflows = {}
    for row in qb.all():
        wf = row[0]
        workflows[wf.pk] = wf
    return list(workflows.values())


if __name__ == "__main__":
    print("=" * 60)
    print("Example: Query IconCalculations by namelist parameters")
    print("=" * 60)

    # Example 1: Find calculations with specific number of vertical levels
    print("\n1. Find IconCalculations with num_lev = 60:")
    calcs = find_icon_calculations_by_model_namelist_param("run_nml", "num_lev", 60)
    print(f"   Found {len(calcs)} calculations")
    for calc in calcs[:5]:
        print(f"   - PK {calc.pk}: {calc.ctime}")
    if len(calcs) > 5:
        print(f"   ... and {len(calcs) - 5} more")

    # Example 2: Find calculations with specific radiation scheme
    print("\n2. Find IconCalculations with inwp_radiation = 4 (ecRad):")
    calcs = find_icon_calculations_by_model_namelist_param(
        "nwp_phy_nml", "inwp_radiation", 4
    )
    print(f"   Found {len(calcs)} calculations")

    # Example 3: Find calculations with specific timestep
    print("\n3. Find IconCalculations with dtime = 2:")
    calcs = find_icon_calculations_by_model_namelist_param("run_nml", "dtime", 2)
    print(f"   Found {len(calcs)} calculations")

    # Example 4: Find workflows containing calculations with specific parameters
    print("\n4. Find workflows with calculations using 60 vertical levels:")
    workflows = find_workflows_by_model_namelist_param("run_nml", "num_lev", 60)
    print(f"   Found {len(workflows)} workflows")
    for wf in workflows[:3]:
        print(f"   - PK {wf.pk}: {wf.label} ({wf.ctime})")

    # Example 5: Query with comparison operators
    print("\n5. Find IconCalculations with msg_level >= 10:")
    qb = QueryBuilder()
    qb.append(IconCalculation, tag="calc", project=["*"])
    qb.append(
        SinglefileData,
        with_outgoing="calc",
        edge_filters={"label": {"like": "models__%"}},
        filters={"attributes.namelist.run_nml.msg_level": {">=": 10}},
    )
    calcs = [row[0] for row in qb.all()]
    print(f"   Found {len(calcs)} calculations")

    print("6. Query by atmosphere model namelist parameters:")
    query_by_model_namelist()
    print()

    print("\n" + "=" * 60)
    print("Query examples complete!")
    print("=" * 60)
