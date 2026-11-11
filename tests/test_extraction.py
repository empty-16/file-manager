import os
import sys
import shutil
import tempfile
import zipfile
import tarfile
import bz2
import gzip
import lzma
import pytest
from PyQt6.QtWidgets import QApplication

# Ensure import works from repo root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import classes & helpers from file-manager
fm = __import__("file-manager")
_get_archive_basename = fm._get_archive_basename
_is_safe_extraction_path = fm._is_safe_extraction_path
_is_decompressible_archive = fm._is_decompressible_archive
_format_size = fm._format_size
_should_extract = fm._should_extract
_list_archive_members = fm._list_archive_members
ExtractWorker = fm.ExtractWorker
ExtractDialog = fm.ExtractDialog
ExtractProgressDialog = fm.ExtractProgressDialog
ArchiveViewer = fm.ArchiveViewer
ArchiveInspectDialog = fm.ArchiveInspectDialog


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["file-manager-test", "-platform", "offscreen"])
    return app


@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp(prefix="fm_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


class TestArchiveHelpers:
    def test_archive_basename(self):
        assert _get_archive_basename("/path/to/archive.zip") == "archive"
        assert _get_archive_basename("package.tar.gz") == "package"
        assert _get_archive_basename("backup.tar.bz2") == "backup"
        assert _get_archive_basename("data.tar.xz") == "data"
        assert _get_archive_basename("release.tgz") == "release"
        assert _get_archive_basename("release.tbz2") == "release"
        assert _get_archive_basename("release.txz") == "release"
        assert _get_archive_basename("archive.7z") == "archive"
        assert _get_archive_basename("document.txt.bz2") == "document.txt"
        assert _get_archive_basename("simple.bz2") == "simple"

    def test_is_safe_extraction_path(self, temp_dir):
        base = os.path.join(temp_dir, "dest")
        os.makedirs(base, exist_ok=True)

        assert _is_safe_extraction_path(base, os.path.join(base, "file.txt"))
        assert _is_safe_extraction_path(base, os.path.join(base, "sub", "dir", "file.txt"))
        # Traversal outside base
        assert not _is_safe_extraction_path(base, os.path.join(base, "..", "evil.txt"))
        assert not _is_safe_extraction_path(base, "/etc/passwd")

    def test_is_decompressible_archive(self, temp_dir):
        zip_path = os.path.join(temp_dir, "test.zip")
        with open(zip_path, "w") as f:
            f.write("dummy")
        assert _is_decompressible_archive(zip_path)

        tar_path = os.path.join(temp_dir, "test.tar.gz")
        with open(tar_path, "w") as f:
            f.write("dummy")
        assert _is_decompressible_archive(tar_path)

        bz2_path = os.path.join(temp_dir, "test.bz2")
        with open(bz2_path, "w") as f:
            f.write("dummy")
        assert _is_decompressible_archive(bz2_path)

        sevenz_path = os.path.join(temp_dir, "test.7z")
        with open(sevenz_path, "w") as f:
            f.write("dummy")
        assert _is_decompressible_archive(sevenz_path)

        txt_path = os.path.join(temp_dir, "test.txt")
        with open(txt_path, "w") as f:
            f.write("dummy")
        assert not _is_decompressible_archive(txt_path)

    def test_format_size(self):
        assert _format_size(None) == ""
        assert _format_size(-1) == ""
        assert _format_size(0) == "0 B"
        assert _format_size(512) == "512 B"
        assert _format_size(1024) == "1.0 KB"
        assert _format_size(1024 * 1024) == "1.0 MB"
        assert _format_size(1024 * 1024 * 1024) == "1.0 GB"

    def test_should_extract(self):
        # When selected_members is None, all members should be extracted
        assert _should_extract("any/path.txt", None) is True

        selected = {"docs", "src/main.py", "README.md"}
        # Exact matches
        assert _should_extract("docs", selected) is True
        assert _should_extract("src/main.py", selected) is True
        assert _should_extract("README.md", selected) is True
        # Child inside selected directory
        assert _should_extract("docs/manual.pdf", selected) is True
        assert _should_extract("docs/sub/guide.txt", selected) is True
        # Unselected members
        assert _should_extract("src/other.py", selected) is False
        assert _should_extract("random.txt", selected) is False

    def test_list_archive_members_zip(self, temp_dir):
        zip_path = os.path.join(temp_dir, "members.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("file1.txt", "contents of file 1")
            zf.writestr("sub/file2.txt", "contents of file 2")

        members = _list_archive_members(zip_path)
        assert len(members) == 2
        names = {m["name"] for m in members}
        assert "file1.txt" in names
        assert "sub/file2.txt" in names
        for m in members:
            if m["name"] == "file1.txt":
                assert m["size"] == len("contents of file 1")
                assert not m["is_dir"]
                assert m["mtime"] is not None

    def test_list_archive_members_tar(self, temp_dir):
        tar_path = os.path.join(temp_dir, "members.tar.gz")
        src_file = os.path.join(temp_dir, "tmp.txt")
        with open(src_file, "w") as f:
            f.write("tar file content")

        with tarfile.open(tar_path, "w:gz") as tf:
            tf.add(src_file, arcname="archived_tmp.txt")

        members = _list_archive_members(tar_path)
        assert len(members) == 1
        assert members[0]["name"] == "archived_tmp.txt"
        assert members[0]["size"] == len("tar file content")
        assert not members[0]["is_dir"]

    def test_list_archive_members_7z(self, temp_dir):
        try:
            import py7zr
        except ImportError:
            pytest.skip("py7zr not installed")

        sz_path = os.path.join(temp_dir, "members.7z")
        src_file = os.path.join(temp_dir, "sz_tmp.txt")
        with open(src_file, "w") as f:
            f.write("7z file content")

        with py7zr.SevenZipFile(sz_path, "w") as zf:
            zf.write(src_file, arcname="sz_archived.txt")

        members = _list_archive_members(sz_path)
        assert len(members) == 1
        assert members[0]["name"] == "sz_archived.txt"
        assert members[0]["size"] == len("7z file content")


class TestDecompression:
    def test_extract_zip(self, temp_dir):
        # Create a sample zip archive
        zip_path = os.path.join(temp_dir, "test.zip")
        dest_dir = os.path.join(temp_dir, "extracted_zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("hello.txt", "Hello Zip World!")
            zf.writestr("sub/nested.txt", "Nested content")

        worker = ExtractWorker([zip_path], dest_dir)
        progress_events = []
        finished_results = []
        worker.progress.connect(lambda cur, tot, name: progress_events.append((cur, tot, name)))
        worker.finished.connect(lambda ok, d, errs: finished_results.append((ok, d, errs)))

        worker.run()

        assert len(finished_results) == 1
        success, final_dest, errors = finished_results[0]
        assert success is True
        assert len(errors) == 0
        assert os.path.exists(os.path.join(dest_dir, "hello.txt"))
        assert open(os.path.join(dest_dir, "hello.txt")).read() == "Hello Zip World!"
        assert os.path.exists(os.path.join(dest_dir, "sub", "nested.txt"))
        assert open(os.path.join(dest_dir, "sub", "nested.txt")).read() == "Nested content"
        assert len(progress_events) == 2

    def test_extract_tar_variants(self, temp_dir):
        # Test .tar, .tar.gz, .tar.bz2, .tar.xz
        variants = [
            ("sample.tar", "w:"),
            ("sample.tar.gz", "w:gz"),
            ("sample.tar.bz2", "w:bz2"),
            ("sample.tar.xz", "w:xz"),
        ]

        for filename, mode in variants:
            tar_path = os.path.join(temp_dir, filename)
            dest_dir = os.path.join(temp_dir, f"out_{filename}")

            # Create tar
            src_file = os.path.join(temp_dir, "tar_src.txt")
            with open(src_file, "w") as f:
                f.write(f"Content for {filename}")

            with tarfile.open(tar_path, mode) as tf:
                tf.add(src_file, arcname="extracted.txt")

            worker = ExtractWorker([tar_path], dest_dir)
            finished_results = []
            worker.finished.connect(lambda ok, d, errs: finished_results.append((ok, d, errs)))
            worker.run()

            success, _, errors = finished_results[0]
            assert success is True, f"Failed for {filename}: {errors}"
            assert open(os.path.join(dest_dir, "extracted.txt")).read() == f"Content for {filename}"

    def test_extract_standalone_bz2(self, temp_dir):
        # Create a standalone .bz2 file
        bz2_path = os.path.join(temp_dir, "sample.txt.bz2")
        dest_dir = os.path.join(temp_dir, "extracted_bz2")

        with bz2.open(bz2_path, "wb") as f:
            f.write(b"Decompressed from standalone bzip2!")

        worker = ExtractWorker([bz2_path], dest_dir)
        finished_results = []
        worker.finished.connect(lambda ok, d, errs: finished_results.append((ok, d, errs)))
        worker.run()

        success, _, errors = finished_results[0]
        assert success is True, f"Bzip2 error: {errors}"
        out_file = os.path.join(dest_dir, "sample.txt")
        assert os.path.exists(out_file)
        assert open(out_file, "rb").read() == b"Decompressed from standalone bzip2!"

    def test_extract_standalone_gz(self, temp_dir):
        gz_path = os.path.join(temp_dir, "sample.txt.gz")
        dest_dir = os.path.join(temp_dir, "extracted_gz")

        with gzip.open(gz_path, "wb") as f:
            f.write(b"Decompressed from standalone gzip!")

        worker = ExtractWorker([gz_path], dest_dir)
        finished_results = []
        worker.finished.connect(lambda ok, d, errs: finished_results.append((ok, d, errs)))
        worker.run()

        success, _, errors = finished_results[0]
        assert success is True, f"Gzip error: {errors}"
        out_file = os.path.join(dest_dir, "sample.txt")
        assert os.path.exists(out_file)
        assert open(out_file, "rb").read() == b"Decompressed from standalone gzip!"

    def test_extract_7z(self, temp_dir):
        # Test 7z if py7zr is available
        try:
            import py7zr
        except ImportError:
            pytest.skip("py7zr not installed in test environment")

        sevenz_path = os.path.join(temp_dir, "sample.7z")
        dest_dir = os.path.join(temp_dir, "extracted_7z")

        src_file = os.path.join(temp_dir, "content.txt")
        with open(src_file, "w") as f:
            f.write("7zip compressed content")

        with py7zr.SevenZipFile(sevenz_path, "w") as z:
            z.write(src_file, arcname="content.txt")

        worker = ExtractWorker([sevenz_path], dest_dir)
        finished_results = []
        worker.finished.connect(lambda ok, d, errs: finished_results.append((ok, d, errs)))
        worker.run()

        success, _, errors = finished_results[0]
        assert success is True, f"7z error: {errors}"
        assert open(os.path.join(dest_dir, "content.txt")).read() == "7zip compressed content"

    def test_zip_slip_protection(self, temp_dir):
        # Malicious zip containing ../evil.txt
        zip_path = os.path.join(temp_dir, "slip.zip")
        dest_dir = os.path.join(temp_dir, "safe_zone")

        with zipfile.ZipFile(zip_path, "w") as zf:
            # Add unsafe member
            zf.writestr("../../evil.txt", "Attacker data")

        worker = ExtractWorker([zip_path], dest_dir)
        finished_results = []
        worker.finished.connect(lambda ok, d, errs: finished_results.append((ok, d, errs)))
        worker.run()

        success, _, errors = finished_results[0]
        assert success is False
        assert len(errors) == 1
        assert "Unsafe path" in errors[0][1]
        assert not os.path.exists(os.path.join(temp_dir, "evil.txt"))

    def test_worker_cancellation(self, temp_dir):
        zip_path = os.path.join(temp_dir, "cancel.zip")
        dest_dir = os.path.join(temp_dir, "cancel_out")

        with zipfile.ZipFile(zip_path, "w") as zf:
            for i in range(10):
                zf.writestr(f"file_{i}.txt", f"data {i}")

        worker = ExtractWorker([zip_path], dest_dir)
        worker.cancel()
        finished_results = []
        worker.finished.connect(lambda ok, d, errs: finished_results.append((ok, d, errs)))
        worker.run()

        success, _, _ = finished_results[0]
        assert success is False

    def test_selective_extract_zip(self, temp_dir):
        zip_path = os.path.join(temp_dir, "selective.zip")
        dest_dir = os.path.join(temp_dir, "sel_out_zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("keep.txt", "Extract me")
            zf.writestr("ignore.txt", "Leave me")
            zf.writestr("folder/sub.txt", "Keep sub")

        # Select keep.txt and folder
        worker = ExtractWorker([zip_path], dest_dir, selected_members=["keep.txt", "folder/sub.txt"])
        finished_results = []
        worker.finished.connect(lambda ok, d, errs: finished_results.append((ok, d, errs)))
        worker.run()

        success, _, errors = finished_results[0]
        assert success is True
        assert os.path.exists(os.path.join(dest_dir, "keep.txt"))
        assert os.path.exists(os.path.join(dest_dir, "folder", "sub.txt"))
        assert not os.path.exists(os.path.join(dest_dir, "ignore.txt"))

    def test_selective_extract_tar(self, temp_dir):
        tar_path = os.path.join(temp_dir, "selective.tar.gz")
        dest_dir = os.path.join(temp_dir, "sel_out_tar")

        f1 = os.path.join(temp_dir, "t1.txt")
        f2 = os.path.join(temp_dir, "t2.txt")
        with open(f1, "w") as f: f.write("one")
        with open(f2, "w") as f: f.write("two")

        with tarfile.open(tar_path, "w:gz") as tf:
            tf.add(f1, arcname="t1.txt")
            tf.add(f2, arcname="t2.txt")

        worker = ExtractWorker([tar_path], dest_dir, selected_members=["t1.txt"])
        finished_results = []
        worker.finished.connect(lambda ok, d, errs: finished_results.append((ok, d, errs)))
        worker.run()

        success, _, errors = finished_results[0]
        assert success is True
        assert os.path.exists(os.path.join(dest_dir, "t1.txt"))
        assert not os.path.exists(os.path.join(dest_dir, "t2.txt"))

    def test_selective_extract_7z(self, temp_dir):
        try:
            import py7zr
        except ImportError:
            pytest.skip("py7zr not installed")

        sz_path = os.path.join(temp_dir, "selective.7z")
        dest_dir = os.path.join(temp_dir, "sel_out_7z")

        f1 = os.path.join(temp_dir, "s1.txt")
        f2 = os.path.join(temp_dir, "s2.txt")
        with open(f1, "w") as f: f.write("one")
        with open(f2, "w") as f: f.write("two")

        with py7zr.SevenZipFile(sz_path, "w") as zf:
            zf.write(f1, arcname="s1.txt")
            zf.write(f2, arcname="s2.txt")

        worker = ExtractWorker([sz_path], dest_dir, selected_members=["s1.txt"])
        finished_results = []
        worker.finished.connect(lambda ok, d, errs: finished_results.append((ok, d, errs)))
        worker.run()

        success, _, errors = finished_results[0]
        assert success is True
        assert os.path.exists(os.path.join(dest_dir, "s1.txt"))
        assert not os.path.exists(os.path.join(dest_dir, "s2.txt"))


class TestUIComponents:
    def test_extract_dialog(self, qapp, temp_dir):
        sample_arc = os.path.join(temp_dir, "archive.zip")
        dlg = ExtractDialog(sample_arc)
        assert dlg.destination() == os.path.join(temp_dir, "archive")
        assert dlg.show_extracted() is True

    def test_progress_dialog(self, qapp):
        prog = ExtractProgressDialog("archive.zip", "/tmp/extracted")
        prog.update_progress(5, 10, "item5.txt")
        assert "item5.txt" in prog._status_lbl.text()
        assert prog._progress_bar.value() == 5
        assert prog._progress_bar.maximum() == 10

    def test_archive_viewer_init_and_selection(self, qapp, temp_dir):
        zip_path = os.path.join(temp_dir, "inspect.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("doc.txt", "Document")
            zf.writestr("src/main.py", "print('hello')")

        viewer = ArchiveViewer(zip_path, default_dest=os.path.join(temp_dir, "out"))
        assert viewer.destination() == os.path.join(temp_dir, "out")
        assert viewer.show_extracted() is True

        # Initially no items selected
        assert len(viewer.selected_members()) == 0

        # Expand all and select all items
        viewer._tree.expandAll()
        viewer._tree.selectAll()
        selected = viewer.selected_members()
        assert "doc.txt" in selected
        assert "src/main.py" in selected

        # Deselect
        viewer._tree.clearSelection()
        assert len(viewer.selected_members()) == 0

    def test_archive_viewer_filtering(self, qapp, temp_dir):
        zip_path = os.path.join(temp_dir, "filter.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("doc.txt", "text")
            zf.writestr("image.png", "img")

        viewer = ArchiveViewer(zip_path)
        # Apply filter for png
        viewer._apply_filter("png")
        assert viewer._item_map["image.png"].isHidden() is False
        assert viewer._item_map["doc.txt"].isHidden() is True

        # Clear filter
        viewer._apply_filter("")
        assert viewer._item_map["image.png"].isHidden() is False
        assert viewer._item_map["doc.txt"].isHidden() is False

    def test_extract_worker_strip_prefixes(self, temp_dir):
        zip_path = os.path.join(temp_dir, "nested.zip")
        dest_dir = os.path.join(temp_dir, "out_stripped")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("sub/folder/file.txt", "nested content")

        # Extract with strip_prefixes=True
        worker = ExtractWorker([zip_path], dest_dir, selected_members=["sub/folder/file.txt"],
                               strip_prefixes=True)
        worker.run()
        # Should be placed directly as file.txt in dest_dir!
        assert os.path.exists(os.path.join(dest_dir, "file.txt"))
        assert open(os.path.join(dest_dir, "file.txt")).read() == "nested content"

    def test_extract_dialog_inspect_flow(self, qapp, temp_dir):
        zip_path = os.path.join(temp_dir, "flow.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("f1.txt", "1")

        dlg = ExtractDialog(zip_path)
        assert dlg.selected_members() is None
        assert dlg._btn_inspect is not None

    def test_drag_and_drop_archive_extraction(self, qapp, temp_dir):
        import json
        from PyQt6.QtCore import QMimeData

        # Create sample archive
        zip_path = os.path.join(temp_dir, "drop.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("dropped.txt", "drag and drop extraction works!")
            zf.writestr("sub/other.txt", "other file")

        # Destination folder
        drop_dest = os.path.join(temp_dir, "drop_target")
        os.makedirs(drop_dest, exist_ok=True)

        # Create MIME payload matching ArchiveViewer's drag
        mime = QMimeData()
        payload = {
            "archive_path": zip_path,
            "members": ["dropped.txt"],
        }
        mime.setData("application/x-archive-extract", json.dumps(payload).encode("utf-8"))

        # Create a TabPane and test _handle_items_dropped
        recent = fm.RecentFiles()
        favorites = fm.Favorites()
        tab = fm.TabPane(recent, [], favorites)
        tab._handle_items_dropped(drop_dest, mime)

        # Verify extracted file in destination
        extracted_file = os.path.join(drop_dest, "dropped.txt")
        assert os.path.exists(extracted_file)
        assert open(extracted_file).read() == "drag and drop extraction works!"
        assert not os.path.exists(os.path.join(drop_dest, "sub", "other.txt"))

    def test_archive_viewer_start_drag_construction(self, qapp, temp_dir):
        from unittest.mock import patch
        zip_path = os.path.join(temp_dir, "drag_test.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("test.txt", "drag test data")

        viewer = ArchiveViewer(zip_path)
        viewer._tree.selectAll()
        assert len(viewer.selected_members()) == 1

        with patch.object(fm.QDrag, "exec", return_value=None):
            viewer._tree._start_drag()

    def test_tabpane_views_accept_drops(self, qapp):
        recent = fm.RecentFiles()
        favorites = fm.Favorites()
        tab = fm.TabPane(recent, [], favorites)

        assert tab.list_view.acceptDrops() is True
        assert tab.list_view.viewport().acceptDrops() is True
        assert tab.list_view.dragDropMode() == fm.QAbstractItemView.DragDropMode.DragDrop

        assert tab.icon_view.acceptDrops() is True
        assert tab.icon_view.viewport().acceptDrops() is True
        assert tab.icon_view.dragDropMode() == fm.QAbstractItemView.DragDropMode.DragDrop

    def test_drag_and_drop_onto_fileview_and_iconview(self, qapp, temp_dir):
        import json
        from PyQt6.QtCore import QMimeData, QPoint, QPointF, Qt
        from PyQt6.QtGui import QDragEnterEvent, QDropEvent

        zip_path = os.path.join(temp_dir, "test_drag.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("file_list.txt", "content for list view")
            zf.writestr("file_icon.txt", "content for icon view")

        cur_dir = os.path.join(temp_dir, "cur_dir")
        os.makedirs(cur_dir, exist_ok=True)
        sub_dir = os.path.join(cur_dir, "target_subfolder")
        os.makedirs(sub_dir, exist_ok=True)

        recent = fm.RecentFiles()
        favorites = fm.Favorites()
        tab = fm.TabPane(recent, [], favorites)
        tab.navigate_to(cur_dir)
        tab.show()
        for _ in range(30):
            qapp.processEvents()

        # 1. Drop onto list_view empty space -> extracts into cur_dir
        mime1 = QMimeData()
        mime1.setData("application/x-archive-extract", json.dumps({
            "archive_path": zip_path,
            "members": ["file_list.txt"],
        }).encode("utf-8"))

        empty_pos = QPoint(50, 400)
        qapp.sendEvent(tab.list_view.viewport(), QDragEnterEvent(
            empty_pos, Qt.DropAction.CopyAction, mime1, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier
        ))
        qapp.sendEvent(tab.list_view.viewport(), QDropEvent(
            QPointF(empty_pos), Qt.DropAction.CopyAction, mime1, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier
        ))
        for _ in range(30):
            qapp.processEvents()

        assert os.path.exists(os.path.join(cur_dir, "file_list.txt"))
        assert open(os.path.join(cur_dir, "file_list.txt")).read() == "content for list view"

        # 2. Drop onto icon_view empty space -> extracts into cur_dir
        tab._view_stack.setCurrentIndex(1)
        for _ in range(20):
            qapp.processEvents()

        mime2 = QMimeData()
        mime2.setData("application/x-archive-extract", json.dumps({
            "archive_path": zip_path,
            "members": ["file_icon.txt"],
        }).encode("utf-8"))

        qapp.sendEvent(tab.icon_view.viewport(), QDragEnterEvent(
            empty_pos, Qt.DropAction.CopyAction, mime2, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier
        ))
        qapp.sendEvent(tab.icon_view.viewport(), QDropEvent(
            QPointF(empty_pos), Qt.DropAction.CopyAction, mime2, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier
        ))
        for _ in range(30):
            qapp.processEvents()

        assert os.path.exists(os.path.join(cur_dir, "file_icon.txt"))
        assert open(os.path.join(cur_dir, "file_icon.txt")).read() == "content for icon view"
