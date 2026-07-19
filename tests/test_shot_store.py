import base64, os, pytest
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import shot_store

# A 1x1 transparent PNG — the smallest real PNG, so the magic-number check is exercised.
PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
DATA_URL = "data:image/png;base64," + base64.b64encode(PNG_1PX).decode()


def test_save_png_writes_the_file_and_returns_a_bare_name(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    name = shot_store.save_png(DATA_URL)
    assert os.sep not in name and name.endswith(".png")
    on_disk = os.path.join(str(tmp_path), "shots", name)
    assert os.path.exists(on_disk)
    with open(on_disk, "rb") as f:
        assert f.read() == PNG_1PX


def test_save_png_names_are_unique(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    names = {shot_store.save_png(DATA_URL) for _ in range(20)}
    assert len(names) == 20


def test_save_png_rejects_a_non_png_data_url(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    with pytest.raises(ValueError):
        shot_store.save_png("data:image/jpeg;base64," + base64.b64encode(PNG_1PX).decode())


def test_save_png_rejects_bytes_that_are_not_actually_a_png(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    bad = "data:image/png;base64," + base64.b64encode(b"not a png at all").decode()
    with pytest.raises(ValueError):
        shot_store.save_png(bad)


def test_save_png_rejects_an_oversized_payload(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    huge = "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"x" * (shot_store.MAX_BYTES + 1)).decode()
    with pytest.raises(ValueError):
        shot_store.save_png(huge)


def test_read_png_round_trips(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    name = shot_store.save_png(DATA_URL)
    assert shot_store.read_png(name) == PNG_1PX


@pytest.mark.parametrize("name", ["../secrets.png", "a/b.png", "", ".", "..", "shot.txt"])
def test_read_png_refuses_a_name_that_is_not_a_plain_png_filename(tmp_path, monkeypatch, name):
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    with pytest.raises(ValueError):
        shot_store.read_png(name)


def test_read_png_missing_file_raises_filenotfound(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    with pytest.raises(FileNotFoundError):
        # 12 hex chars — the shape save_png() actually generates (secrets.token_hex(6)).
        # A well-formed name that is simply absent must reach the open() and raise
        # FileNotFoundError, not be turned away by the name check.
        shot_store.read_png("2026-01-01T00-00-00-abcdef123456.png")
