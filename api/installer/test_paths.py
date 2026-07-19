"""
Destination-path parsing/validation — this value ends up as a literal
filesystem path on every customer's machine, so the validation rules here
are a real security boundary (path traversal, drive-letter escape), not
just UX polish.
"""
import pytest

from installer.paths import ADDIN_DIR_TOKEN, INSTALL_DIR_TOKEN, InvalidDestinationPath, parse_destination_path


def test_bare_token_resolves_to_empty_segments():
    token, segments = parse_destination_path(ADDIN_DIR_TOKEN)
    assert token == ADDIN_DIR_TOKEN
    assert segments == []


def test_token_with_subpath():
    token, segments = parse_destination_path(r"{INSTALL_DIR}\lib\dependency.dll")
    assert token == INSTALL_DIR_TOKEN
    assert segments == ["lib", "dependency.dll"]


def test_forward_slashes_also_accepted():
    _, segments = parse_destination_path("{ADDIN_DIR}/Resources/icon.png")
    assert segments == ["Resources", "icon.png"]


@pytest.mark.parametrize(
    "raw",
    [
        r"{ADDIN_DIR}\..\..\Windows\System32\evil.dll",
        r"{INSTALL_DIR}\..\escape.dll",
        r"C:\Windows\System32\evil.dll",
        r"{UNKNOWN_TOKEN}\file.dll",
        "",
        r"{ADDIN_DIR}\<script>.dll",
    ],
)
def test_rejects_unsafe_or_invalid_paths(raw):
    with pytest.raises(InvalidDestinationPath):
        parse_destination_path(raw)


def test_rejects_bare_drive_letter_segment():
    with pytest.raises(InvalidDestinationPath):
        parse_destination_path(r"{ADDIN_DIR}\C:\file.dll")
