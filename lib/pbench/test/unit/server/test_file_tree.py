import re
import hashlib
import shutil

import pytest

from pbench.common.logger import get_pbench_logger
from pbench.server.filetree import BadFilename, DatasetNotFound, DuplicateDataset, FileTree, Tarball


@pytest.fixture
def make_logger(server_config):
    return get_pbench_logger("TEST", server_config)


@pytest.fixture(scope="function", autouse=True)
def file_sweeper(server_config):
    trees = [server_config.ARCHIVE, server_config.INCOMING, server_config.RESULTS]

    for tree in trees:
        tree.mkdir(parents=True, exist_ok=True)

    yield

    # After each test case:

    for tree in trees:
        for d in tree.iterdir():
            if d.is_dir():
                shutil.rmtree(d, ignore_errors=True)
            else:
                d.unlink()


class TestFileTree:
    def test_create(self, server_config, make_logger):
        tree = FileTree(server_config, make_logger)
        assert tree is not None
        assert not tree.datasets  # No datasets expected
        assert not tree.controllers  # No controllers expected

        temp = re.compile(r"^(.*)/srv/pbench")
        match = temp.match(str(tree.archive_root))
        root = match.group(1)
        assert str(tree.archive_root) == root + "/srv/pbench/archive/fs-version-001"
        assert str(tree.incoming_root) == root + "/srv/pbench/public_html/incoming"
        assert str(tree.results_root) == root + "/srv/pbench/public_html/results"

    def test_discover_empties(self, server_config, make_logger):
        tree = FileTree(server_config, make_logger)
        tree.full_discovery()
        assert not tree.datasets  # No datasets expected
        assert not tree.controllers  # No controllers expected

    def test_empty_controller(self, server_config, make_logger):
        tree = FileTree(server_config, make_logger)
        test_controller = tree.archive_root / "TEST"
        test_controller.mkdir()
        tree.full_discovery()
        assert not tree.datasets  # No datasets expected
        assert list(tree.controllers.keys()) == ["TEST"]

    def test_clean_emptys(self, server_config, make_logger):
        tree = FileTree(server_config, make_logger)
        controllers = ["PLUGH", "XYZZY"]
        roots = [tree.archive_root, tree.incoming_root, tree.results_root]
        for c in controllers:
            for r in roots:
                d = r / c
                d.mkdir(parents=True)
        tree.full_discovery()
        ctrls = sorted(list(tree.controllers.keys()))
        assert ctrls == controllers

        for c in controllers:
            tree._clean_empties(c)
        assert not tree.controllers
        for c in controllers:
            for r in roots:
                assert not (r / c).exists()

    def test_create_bad(self, monkeypatch, server_config, make_logger, tarball):
        # Calling restorecon() gives warning messages about "no default label"
        monkeypatch.setattr("selinux.restorecon", lambda a: None)

        source_tarball, source_md5, md5 = tarball
        dataset_name = Tarball.stem(source_tarball)
        tree = FileTree(server_config, make_logger)

        # Attempting to create a dataset from the md5 file should result in
        # a bad filename error
        with pytest.raises(BadFilename) as exc:
            tree.create("ABC", source_md5)
        assert type(exc.value) is BadFilename
        assert exc.value.path == str(source_md5)

        tree.create("ABC", source_tarball)

        # The create will remove the source files, so trying again should
        # result in an error.
        with pytest.raises(BadFilename) as exc:
            tree.create("ABC", source_md5)
        assert type(exc.value) is BadFilename
        assert exc.value.path == str(source_md5)

        # Attempting to create the same dataset again (from the archive copy)
        # should fail with a duplicate dataset error.
        tarball = tree.find_dataset(dataset_name)
        with pytest.raises(DuplicateDataset) as exc:
            tree.create("ABC", tarball.tarball_path)
        assert type(exc.value) is DuplicateDataset
        assert str(exc.value) == "A dataset named 'pbench-user-benchmark_some + config_2021.05.01T12.42.42' is already present in the file tree"
        assert exc.value.dataset == tarball.name

    def test_find(self, monkeypatch, server_config, make_logger, tarball):
        # Calling restorecon() gives warning messages about "no default label"
        monkeypatch.setattr("selinux.restorecon", lambda a: None)

        source_tarball, source_md5, md5 = tarball
        dataset_name = Tarball.stem(source_tarball)
        tree = FileTree(server_config, make_logger)
        tree.create("ABC", source_tarball)

        # The original files should have been removed
        assert not source_tarball.exists()
        assert not source_md5.exists()

        tarball = tree.find_dataset(dataset_name)
        assert tarball
        assert tarball.name == dataset_name

        # Test __getitem__
        assert tarball == tree[dataset_name]
        with pytest.raises(DatasetNotFound) as exc:
            tree["foobar"]
        assert type(exc.value) is DatasetNotFound
        assert str(exc.value) == "The dataset named 'foobar' is not present in the file tree"

        # Test __contains__
        assert dataset_name in tree
        assert "foobar" not in tree

        # Try to find a dataset that doesn't exist
        with pytest.raises(DatasetNotFound) as exc:
            tree.find_dataset("foobar")
        assert type(exc.value) is DatasetNotFound
        assert str(exc.value) == "The dataset named 'foobar' is not present in the file tree"
        assert exc.value.dataset == "foobar"

        # We should be able to find the tarball even in a new file tree
        # that hasn't been fully discovered.
        new = FileTree(server_config, make_logger)
        assert dataset_name not in new

        tarball = new.find_dataset(dataset_name)
        assert tarball
        assert tarball.name == dataset_name
        assert list(new.controllers.keys()) == ["ABC"]
        assert list(new.datasets.keys()) == [dataset_name]

    def test_lifecycle(self, monkeypatch, server_config, make_logger, tarball):

        # Calling restorecon() gives warning messages about "no default label"
        monkeypatch.setattr("selinux.restorecon", lambda a: None)

        source_tarball, source_md5, md5 = tarball
        tree = FileTree(server_config, make_logger)
        tree.create("ABC", source_tarball)
        archive = tree.archive_root / "ABC"
        incoming = tree.incoming_root / "ABC"
        results = tree.results_root / "ABC"

        # Expect the archive directory was created, but we haven't unpacked so
        # incoming and results should not exist.
        assert archive.is_dir()
        assert not incoming.exists()
        assert not results.exists()

        # The original files should have been removed
        assert not source_tarball.exists()
        assert not source_md5.exists()

        tarfile = archive / source_tarball.name
        md5file = archive / source_md5.name
        assert tarfile.exists()
        assert md5file.exists()

        todo_state = archive / "TODO" / tarfile.name
        assert todo_state.is_symlink()
        assert todo_state.samefile(tarfile)

        assert md5 == md5file.read_text()
        hash = hashlib.md5()
        hash.update(tarfile.read_bytes())
        assert md5 == hash.hexdigest()

        assert list(tree.controllers.keys()) == ["ABC"]
        dataset_name = source_tarball.name[:-7]
        assert list(tree.datasets.keys()) == [dataset_name]

        # Now "unpack" the tarball and check that the incoming directory and
        # results link are set up.
        incoming_dir = incoming / dataset_name
        results_link = results / dataset_name
        tree.unpack(dataset_name)
        assert incoming_dir.is_dir()
        assert results_link.is_symlink()
        assert results_link.samefile(incoming_dir)

        # Re-discover, with all the files in place, and compare
        newtree = FileTree(server_config, make_logger)
        newtree.full_discovery()

        assert newtree.archive_root == tree.archive_root
        assert newtree.incoming_root == tree.incoming_root
        assert newtree.results_root == tree.results_root
        assert sorted(list(newtree.controllers.keys())) == sorted(
            list(tree.controllers.keys())
        )
        assert sorted(list(newtree.datasets.keys())) == sorted(
            list(tree.datasets.keys())
        )
        for controller in tree.controllers.values():
            other = newtree.controllers[controller.name]
            assert controller.name == other.name
            assert controller.path == other.path
            assert sorted(list(controller.tarballs.keys())) == sorted(
                list(other.tarballs.keys())
            )
        for tarball in tree.datasets.values():
            other = newtree.datasets[tarball.name]
            assert tarball.name == other.name
            assert tarball.controller_name == other.controller_name
            assert tarball.tarball_path == other.tarball_path
            assert tarball.md5_path == other.md5_path
            assert tarball.unpacked == other.unpacked
            assert tarball.results_link == other.results_link

        # Remove the unpacked tarball, and confirm that the directory and link
        # are removed.
        tree.uncache(dataset_name)
        assert not results_link.exists()
        assert not incoming_dir.exists()

        # Now that we have all that setup, delete the dataset
        tree.delete(dataset_name)
        assert not archive.exists()
        assert not tree.controllers
        assert not tree.datasets