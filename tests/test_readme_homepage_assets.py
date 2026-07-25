from __future__ import annotations

from pathlib import Path

from PIL import Image

from scripts import validate_benchmark_kb


ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "docs/assets/readme"
REQUIRED_ASSETS = {
    "docs/assets/readme/pep_design_icon_v1.png",
    "docs/assets/readme/pep_design_homepage_workflow_v1.png",
    "docs/assets/readme/readme_imagegen_record_v1.md",
}


def test_readme_imagegen_assets_are_registered_and_present() -> None:
    assert REQUIRED_ASSETS <= set(validate_benchmark_kb.REQUIRED_FILES)
    assert all((ROOT / relative).is_file() for relative in REQUIRED_ASSETS)


def test_readme_icon_has_transparent_corners_and_visible_subject() -> None:
    with Image.open(ASSET_ROOT / "pep_design_icon_v1.png") as image:
        assert image.mode == "RGBA"
        assert image.width == image.height
        alpha = image.getchannel("A")
        assert alpha.getextrema() == (0, 255)
        assert {
            alpha.getpixel((0, 0)),
            alpha.getpixel((image.width - 1, 0)),
            alpha.getpixel((0, image.height - 1)),
            alpha.getpixel((image.width - 1, image.height - 1)),
        } == {0}
        visible = sum(value > 0 for value in alpha.getdata())
        assert visible > image.width * image.height * 0.1


def test_readme_workflow_is_wide_and_readable_at_github_scale() -> None:
    with Image.open(
        ASSET_ROOT / "pep_design_homepage_workflow_v1.png"
    ) as image:
        assert image.mode == "RGB"
        assert image.width >= 1600
        assert image.height >= 900
        assert image.width / image.height >= 1.7
