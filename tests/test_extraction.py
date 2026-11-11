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
ExtractWorker = fm.ExtractWorker
ExtractDialog = fm.ExtractDialog
ExtractProgressDialog = fm.ExtractProgressDialog


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
