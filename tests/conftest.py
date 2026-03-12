"""Shared test fixtures for Lens Studio CLI tests."""

import json
import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_dir():
    """Provide a temporary directory for test projects."""
    with tempfile.TemporaryDirectory(prefix="ls_cli_test_") as d:
        yield d


@pytest.fixture
def sample_project(tmp_dir):
    """Create a sample project and return (project_data, project_path, project_dir)."""
    from cli_anything.lens_studio.core.project import create_project, load_project

    result = create_project("TestProject", directory=tmp_dir, template="blank")
    data = load_project(result["path"])
    return data, result["path"], result["directory"]


@pytest.fixture
def face_project(tmp_dir):
    """Create a face-effects project."""
    from cli_anything.lens_studio.core.project import create_project, load_project

    result = create_project("FaceProject", directory=tmp_dir, template="face-effects")
    data = load_project(result["path"])
    return data, result["path"], result["directory"]


@pytest.fixture
def sample_texture(tmp_dir):
    """Create a sample texture file for import tests."""
    tex_path = Path(tmp_dir) / "test_texture.png"
    import struct
    import zlib

    def minimal_png():
        signature = b'\x89PNG\r\n\x1a\n'
        ihdr_data = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)
        ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data) & 0xffffffff
        ihdr = struct.pack('>I', 13) + b'IHDR' + ihdr_data + struct.pack('>I', ihdr_crc)
        raw = zlib.compress(b'\x00\xff\x00\x00')
        idat_crc = zlib.crc32(b'IDAT' + raw) & 0xffffffff
        idat = struct.pack('>I', len(raw)) + b'IDAT' + raw + struct.pack('>I', idat_crc)
        iend_crc = zlib.crc32(b'IEND') & 0xffffffff
        iend = struct.pack('>I', 0) + b'IEND' + struct.pack('>I', iend_crc)
        return signature + ihdr + idat + iend

    tex_path.write_bytes(minimal_png())
    return str(tex_path)
