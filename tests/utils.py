import pathlib

import aiida


def assert_output_streams(res, node, expected_streams_and_files: dict[str, list[str]]):
    """
    Utility function to test output streams structure and contents.

    Args:
        res: The calculation result dictionary
        node: The calculation node
        expected_streams_and_files: Dict mapping stream names to expected file lists
    """

    output_streams = res.get("output_streams", None)

    if not output_streams:
        return

    # Test structure and keys
    expected_keys = set(expected_streams_and_files.keys())
    assert (
        set(output_streams.keys()) == expected_keys
    ), f"Expected keys {expected_keys}, got {set(output_streams.keys())}"

    # Test node outputs
    assert hasattr(node.outputs, "output_streams"), "No output_streams attached as node outputs."
    assert all(
        hasattr(node.outputs.output_streams, key) for key in expected_keys
    ), "Not the right outputs attached to the output_streams AttributeDict."

    # Test all values are RemoteData
    assert all(
        isinstance(stream, aiida.orm.RemoteData) for stream in output_streams.values()
    ), "All output streams should be RemoteData"

    # Test file names within each stream directory
    for stream_name, expected_files in expected_streams_and_files.items():
        stream_remote = output_streams[stream_name]
        stream_path = stream_remote.get_remote_path()
        computer = stream_remote.computer

        with computer.get_transport() as transport:
            if transport.isdir(stream_path):
                all_items = transport.listdir(stream_path)

                actual_files = []
                for item in all_items:
                    item_path = pathlib.Path(stream_path) / item
                    if transport.isfile(item_path):
                        actual_files.append(item)

                assert set(actual_files) == set(expected_files), (
                    f"Stream '{stream_name}' expected files {expected_files}, " f"got {actual_files} in {stream_path}"
                )
            else:
                msg = f"Stream directory '{stream_path}' does not exist on remote computer"
                raise AssertionError(msg)
