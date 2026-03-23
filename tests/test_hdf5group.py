from pathlib import Path

from h5py import File
import pytest

from larch.io.hdf5group import h5group


class TestHDF5Group:
    @pytest.mark.parametrize(
        ["shape"],
        [pytest.param(()), pytest.param((1)), pytest.param((1, 1))],
    )
    def test_h5group_singular_bytes(self, tmp_path: Path, shape: tuple) -> None:
        tmp_filepath = tmp_path / "test.h5"
        with File(tmp_filepath, "w") as f:
            f.create_dataset("test", shape=shape, dtype="|S3", data=b"abc")

        group = h5group(tmp_filepath)
        assert hasattr(group, "test")
        assert group.test == "abc"

    def test_h5group_array_bytes(self, tmp_path: Path) -> None:
        tmp_filepath = tmp_path / "test.h5"
        with File(tmp_filepath, "w") as f:
            f.create_dataset("test", shape=(2), dtype="|S3", data=[b"abc", b"def"])

        group = h5group(tmp_filepath)
        assert hasattr(group, "test")
        assert group.test == ["abc", "def"]
