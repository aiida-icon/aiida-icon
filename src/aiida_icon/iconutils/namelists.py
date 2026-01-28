import io
import pathlib
import typing

import aiida.orm
import f90nml

NMLInput: typing.TypeAlias = aiida.orm.SinglefileData | f90nml.namelist.Namelist

# Type alias for JSON-serializable namelist values
# This is more precise than typing.Any - it explicitly represents the valid
# types that can appear in a serialized namelist
JSONValue: typing.TypeAlias = str | int | float | bool | None | list["JSONValue"] | dict[str, "JSONValue"]


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


def namelist_to_dict(nml: f90nml.namelist.Namelist) -> dict[str, list[dict[str, JSONValue]]]:
    """Convert f90nml.Namelist to nested dict for JSON serialization.

    Recursively converts f90nml.Namelist objects to plain Python dicts,
    which can be stored in AiiDA node attributes for queryability.

    Each top-level namelist group is always represented as a list, even if there's
    only one occurrence. This provides consistent structure and better type safety.

    Args:
        nml: An f90nml.Namelist object.

    Returns:
        A nested dictionary where each key maps to a list of namelist group dicts.

    Example:
        >>> import f90nml
        >>> nml_content = '''
        ... &run_nml
        ...   num_lev = 60
        ...   dtime = 10.0
        ... /
        ... &grid_nml
        ...   dynamics_grid_filename = 'grid.nc'
        ... /
        ... '''
        >>> nml = f90nml.reads(nml_content)
        >>> result = namelist_to_dict(nml)
        >>> result["run_nml"]
        [{'num_lev': 60, 'dtime': 10.0}]
        >>> result["grid_nml"]
        [{'dynamics_grid_filename': 'grid.nc'}]
    """
    # Get unique keys and their values in one pass
    all_keys = list(nml.keys())
    unique_keys = list(dict.fromkeys(all_keys))  # Preserve order, remove duplicates

    # Build result where each key always maps to a list
    result: dict[str, list[dict[str, JSONValue]]] = {}
    for key in unique_keys:
        if all_keys.count(key) > 1:
            # This key has duplicates - collect all occurrences as a list
            # Use items() which yields each occurrence separately
            values = [v for k, v in nml.items() if k == key]
            result[key] = [typing.cast("dict[str, JSONValue]", _namelist_to_dict_recursive(v)) for v in values]
        else:
            # Single occurrence - still wrap in a list for consistency
            result[key] = [typing.cast("dict[str, JSONValue]", _namelist_to_dict_recursive(nml[key]))]
    return result


def _namelist_to_dict_recursive(
    nml: f90nml.namelist.Namelist | f90nml.namelist.Cogroup | JSONValue,
) -> JSONValue:
    """Internal recursive helper for converting nested namelist structures.

    This function handles the recursion through nested Namelists, Cogroups,
    dicts, lists, and primitive values.
    """
    # Check for Cogroup first (list of duplicate namelist groups)
    # Cogroup inherits from both list and dict, so check it before dict
    if isinstance(nml, f90nml.namelist.Cogroup):
        return [_namelist_to_dict_recursive(item) for item in nml]
    if isinstance(nml, f90nml.namelist.Namelist):
        # Recursively convert nested namelist
        return {key: _namelist_to_dict_recursive(value) for key, value in nml.items()}
    if isinstance(nml, dict):
        return {key: _namelist_to_dict_recursive(value) for key, value in nml.items()}
    if isinstance(nml, list):
        return [_namelist_to_dict_recursive(item) for item in nml]
    # Primitive value (str, int, float, bool, None, etc.)
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

    Args:
        source: Path to the namelist file (string or Path object).
        store: If True, store the node immediately. Default is True.

    Returns:
        A SinglefileData node with the namelist file and parsed content
        in attributes under the 'namelist' key.

    Example:
        >>> import tempfile
        >>> import os
        >>> nml_content = "&run_nml\\n  num_lev = 60\\n/\\n"
        >>> with tempfile.NamedTemporaryFile(mode="w", suffix=".nml", delete=False) as f:
        ...     _ = f.write(nml_content)
        ...     tmpfile = f.name
        >>> node = create_namelist_singlefiledata(tmpfile, store=False)
        >>> node.base.attributes.get("namelist")
        {'run_nml': [{'num_lev': 60}]}
        >>> os.unlink(tmpfile)  # cleanup
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

    Args:
        content: The namelist content as a string.
        filename: The filename to use for the SinglefileData. Default is 'namelist.nml'.
        store: If True, store the node immediately. Default is True.

    Returns:
        A SinglefileData node with the namelist content and parsed data
        in attributes under the 'namelist' key.

    Example:
        >>> nml_content = "&run_nml\\n  num_lev = 60\\n  dtime = 10.0\\n/\\n"
        >>> node = create_namelist_singlefiledata_from_content(nml_content, store=False)
        >>> node.base.attributes.get("namelist")
        {'run_nml': [{'num_lev': 60, 'dtime': 10.0}]}
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
