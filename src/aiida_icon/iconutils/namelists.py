import io
import pathlib
import typing

import aiida.orm
import f90nml

NMLInput: typing.TypeAlias = aiida.orm.SinglefileData | f90nml.namelist.Namelist


def namelists_data(
    namelist: NMLInput,
) -> f90nml.namelist.Namelist:
    match namelist:
        case f90nml.namelist.Namelist():
            return namelist
        case aiida.orm.SinglefileData():
            return f90nml.reads(namelist.get_content(mode="r"))
        case _:
            raise ValueError


def namelist_to_dict(nml: f90nml.namelist.Namelist | typing.Any) -> dict | typing.Any:
    """Convert f90nml.Namelist to nested dict for JSON serialization.

    Recursively converts f90nml.Namelist objects to plain Python dicts,
    which can be stored in AiiDA node attributes for queryability.

    :param nml: An f90nml.Namelist object or any nested structure containing them.
    :returns: A nested dictionary representation suitable for AiiDA attributes.
    """
    if isinstance(nml, f90nml.namelist.Namelist):
        return {key: namelist_to_dict(value) for key, value in nml.items()}
    elif isinstance(nml, dict):
        return {key: namelist_to_dict(value) for key, value in nml.items()}
    elif isinstance(nml, list):
        return [namelist_to_dict(item) for item in nml]
    else:
        return nml


def create_namelist_singlefiledata(
    source: str | pathlib.Path,
    *,
    store: bool = True,
) -> aiida.orm.SinglefileData:
    """Create a SinglefileData node with parsed namelist content in attributes.

    This function creates a SinglefileData node from a namelist file and
    automatically parses its content, storing the parsed dictionary in the
    node's attributes. This enables querying on namelist parameters.

    :param source: Path to the namelist file (string or Path object).
    :param store: If True, store the node immediately. Default is True.
    :returns: A SinglefileData node with the namelist file and parsed content
        in attributes under the 'namelist' key.

    Example::

        >>> node = create_namelist_singlefiledata("/path/to/NAMELIST_atm")
        >>> node.base.attributes.get('namelist')
        {'PARALLEL_NML': {'nproma': 0, ...}, 'RUN_NML': {'num_lev': 60, ...}, ...}

        # Query example:
        >>> qb = QueryBuilder()
        >>> qb.append(SinglefileData, filters={
        ...     'attributes.namelist.RUN_NML.num_lev': 60
        ... })
    """
    filepath = pathlib.Path(source)

    # Read and parse the namelist content
    with filepath.open("r") as fhandle:
        content = fhandle.read()

    nml = f90nml.reads(content)
    nml_dict = namelist_to_dict(nml)

    # Create SinglefileData node
    node = aiida.orm.SinglefileData(file=filepath)

    # Store parsed namelist in attributes for queryability
    node.base.attributes.set("namelist", nml_dict)

    if store:
        node.store()

    return node


def create_namelist_singlefiledata_from_content(
    content: str,
    filename: str = "namelist.nml",
    *,
    store: bool = True,
) -> aiida.orm.SinglefileData:
    """Create a SinglefileData node from namelist content string.

    Similar to create_namelist_singlefiledata but takes the namelist content
    directly as a string instead of a file path.

    :param content: The namelist content as a string.
    :param filename: The filename to use for the SinglefileData. Default is 'namelist.nml'.
    :param store: If True, store the node immediately. Default is True.
    :returns: A SinglefileData node with the namelist content and parsed data
        in attributes under the 'namelist' key.
    """
    nml = f90nml.reads(content)
    nml_dict = namelist_to_dict(nml)

    # Create SinglefileData from content using file-like object
    file_obj = io.BytesIO(content.encode("utf-8"))
    node = aiida.orm.SinglefileData(file=file_obj, filename=filename)

    # Store parsed namelist in attributes for queryability
    node.base.attributes.set("namelist", nml_dict)

    if store:
        node.store()

    return node
