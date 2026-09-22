import json

import cv2
import numpy as np
import pytest

from labsight.cli import main


def _write_structured_image(path):
    image = np.zeros((128, 128), dtype=np.uint8)
    cv2.rectangle(image, (20, 20), (108, 108), 180, -1)
    cv2.circle(image, (64, 64), 24, 60, -1)
    assert cv2.imwrite(str(path), image)


def test_cli_emits_machine_readable_qc_report(tmp_path, capsys):
    image_path = tmp_path / "sample.png"
    _write_structured_image(image_path)

    assert main([str(image_path)]) == 0
    report = json.loads(capsys.readouterr().out)

    assert report["purpose"] == "microscopy_image_quality_control_only"
    assert report["diagnostic_claims"] is False
    assert report["source"] == str(image_path)
    assert report["status"] in {
        "accept",
        "request_recapture_focus",
        "request_recapture_exposure",
        "human_review",
    }
    assert report["trace"]


def test_cli_writes_same_report_to_output_file(tmp_path, capsys):
    image_path = tmp_path / "sample.png"
    output_path = tmp_path / "evidence" / "qc.json"
    _write_structured_image(image_path)

    assert main([str(image_path), "--output", str(output_path)]) == 0
    stdout_report = json.loads(capsys.readouterr().out)
    file_report = json.loads(output_path.read_text(encoding="utf-8"))
    assert file_report == stdout_report


def test_cli_rejects_missing_image_without_traceback(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        main([str(tmp_path / "missing.png")])
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "image does not exist or is not a file" in captured.err


def test_cli_rejects_undecodable_input(tmp_path, capsys):
    bad = tmp_path / "not-an-image.png"
    bad.write_text("not image bytes", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        main([str(bad)])
    assert exc.value.code == 2
    assert "OpenCV could not decode image" in capsys.readouterr().err
