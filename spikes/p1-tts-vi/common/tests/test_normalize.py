from pathlib import Path

import pytest

from tts_common import (
    DEFAULT_PRONUNCIATIONS,
    PRONUNCIATIONS_BY_PROVIDER,
    load_pronunciations,
    normalize_vi,
    normalizer_for,
    pronunciations_for,
)
from tts_common.numbers_vi import read_int


@pytest.mark.parametrize(
    ("digits", "expected"),
    [
        ("0", "không"),
        ("5", "năm"),
        ("10", "mười"),
        ("11", "mười một"),
        ("14", "mười bốn"),
        ("15", "mười lăm"),
        ("21", "hai mươi mốt"),
        ("24", "hai mươi tư"),
        ("25", "hai mươi lăm"),
        ("100", "một trăm"),
        ("105", "một trăm lẻ năm"),
        ("390000", "ba trăm chín mươi nghìn"),
        ("1000", "một nghìn"),
        ("1250000", "một triệu hai trăm năm mươi nghìn"),
        ("2026", "hai nghìn không trăm hai mươi sáu"),
        ("2005", "hai nghìn không trăm lẻ năm"),
        ("1000000", "một triệu"),
        ("2000000000", "hai tỷ"),
    ],
)
def test_read_int(digits: str, expected: str) -> None:
    assert read_int(digits) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # giá
        ("390.000đ", "ba trăm chín mươi nghìn đồng"),
        ("390.000 đồng", "ba trăm chín mươi nghìn đồng"),
        ("390k", "ba trăm chín mươi nghìn"),
        ("Giá 1.250.000₫", "Giá một triệu hai trăm năm mươi nghìn đồng"),
        ("1,2 triệu", "một phẩy hai triệu"),
        ("1,2 triệu đ", "một phẩy hai triệu đồng"),
        ("$17", "mười bảy đô la"),
        ("17 USD", "mười bảy đô la Mỹ"),
        # phần trăm, thập phân
        ("giảm 25%", "giảm hai mươi lăm phần trăm"),
        ("tăng 12,5 %", "tăng mười hai phẩy năm phần trăm"),
        ("3.5 lít", "ba phẩy năm lít"),
        ("0,05", "không phẩy không năm"),
        # đơn vị
        ("500ml", "năm trăm mi li lít"),
        ("500 ml", "năm trăm mi li lít"),
        ("1,2 kg", "một phẩy hai ki lô gam"),
        ("30°C", "ba mươi độ xê"),
        ("15 phút", "mười lăm phút"),
        ("12 giờ", "mười hai giờ"),
        # khoảng, giờ, ngày, số điện thoại
        ("2-3 ngày", "hai đến ba ngày"),
        ("15–25 giây", "mười lăm đến hai mươi lăm giây"),
        ("9h30", "chín giờ ba mươi"),
        ("9h", "chín giờ"),
        ("8:05", "tám giờ lẻ năm"),
        ("trước ngày 31/10/2026", "trước ngày ba mươi mốt tháng mười năm hai nghìn không trăm hai mươi sáu"),
        ("14/10/2026", "ngày mười bốn tháng mười năm hai nghìn không trăm hai mươi sáu"),
        ("hết ngày 5/10", "hết ngày năm tháng mười"),
        ("hạn 10/2026", "hạn tháng mười năm hai nghìn không trăm hai mươi sáu"),
        ("gọi 0909 123 456", "gọi không chín không chín một hai ba bốn năm sáu"),
        # KHÔNG được hiểu nhầm là ngày
        ("pha 1/2 ly", "pha một phần hai ly"),
        ("5-10 phút", "năm đến mười phút"),
        # số dính chữ thì để nguyên
        ("mp3", "mp3"),
    ],
)
def test_numbers_money_units(text: str, expected: str) -> None:
    assert normalize_vi(text, pronunciations=None) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Gói Pro của ElevenLabs", "Gói Prô của I lép ven Láp"),
        ("Bình Lock&Lock 500ml", "Bình Lốc en Lốc năm trăm mi li lít"),
        ("Dùng AI tạo video", "Dùng ây ai tạo Vi đi ô"),
        ("ai cũng biết", "ai cũng biết"),  # "ai" thường (đại từ) không bị đổi thành "ây ai"
        ("ở TP.HCM", "ở Thành phố Hồ Chí Minh"),
    ],
)
def test_pronunciations(text: str, expected: str) -> None:
    assert normalize_vi(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # QA 21/10: ElevenLabs để nguyên (4-5/5), phiên âm "I lép ven Láp" chỉ 2/5 trên cả 3 cấu hình VieNeu
        ("Gói Pro của ElevenLabs", "Gói Prô của ElevenLabs"),
        # `&` -> "en" (Lock&Lock 5/5); tên giữ nguyên, không phiên âm "Lốc"
        ("Bình Lock&Lock 500ml", "Bình Lock en Lock năm trăm mi li lít"),
        # chưa đổi: QA chưa nghe bản để nguyên của Starter/Pro
        ("Gói Starter", "Gói Sờ ta tơ"),
        ("Dùng AI tạo video", "Dùng ây ai tạo Vi đi ô"),
    ],
)
def test_pronunciations_vieneu(text: str, expected: str) -> None:
    assert normalizer_for("vieneu")(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Gói Pro của ElevenLabs", "Gói Prô của I lép ven Láp"),
        ("Bình Lock&Lock 500ml", "Bình Lốc en Lốc năm trăm mi li lít"),
        ("Gói Starter", "Gói Sờ ta tơ"),
    ],
)
def test_pronunciations_piper_unchanged(text: str, expected: str) -> None:
    assert normalizer_for("piper")(text) == expected


def test_provider_tables() -> None:
    piper, vieneu = pronunciations_for("piper"), pronunciations_for("vieneu")
    assert piper == DEFAULT_PRONUNCIATIONS  # Piper giữ bảng cũ
    assert set(piper) - set(vieneu) == {"ElevenLabs", "Lock&Lock"}
    assert all(vieneu[k] == piper[k] for k in vieneu)  # mục còn lại CHƯA đổi, không suy rộng từ ElevenLabs
    assert {"Starter", "Pro"} <= set(vieneu)
    with pytest.raises(KeyError, match="gemini"):
        pronunciations_for("gemini")


def test_load_pronunciations_merges_onto_provider_table(tmp_path: Path) -> None:
    f = tmp_path / "p.json"
    f.write_text('{"PDF": "pi đi ép"}', encoding="utf-8")
    assert load_pronunciations(f)["ElevenLabs"] == "I lép ven Láp"  # mặc định = Piper (giữ hành vi cũ)
    vieneu = load_pronunciations(f, "vieneu")
    assert "ElevenLabs" not in vieneu
    assert vieneu["PDF"] == "pi đi ép"


@pytest.mark.parametrize(
    "pron", [None, {}, PRONUNCIATIONS_BY_PROVIDER["piper"], PRONUNCIATIONS_BY_PROVIDER["vieneu"]]
)
def test_ampersand_is_en_for_every_provider(pron: dict[str, str] | None) -> None:
    # quy tắc ký hiệu ở bước chuẩn hoá, không phụ thuộc bảng phát âm
    assert normalize_vi("Tom&Jerry", pron) == "Tom en Jerry"
    assert normalize_vi("Tom & Jerry", pron) == "Tom en Jerry"


def test_pronunciations_can_be_disabled_and_extended() -> None:
    assert normalize_vi("Gói Pro", pronunciations=None) == "Gói Pro"
    assert normalize_vi("Gói Pro", pronunciations={"Pro": "pờ rô"}) == "Gói pờ rô"


def test_acronym_fallback_spells_letters() -> None:
    assert normalize_vi("CTA") == "xi ti ây"
    assert normalize_vi("CTA", spell_acronyms=False) == "CTA"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # dấu chấm/phẩy/! cuối câu không được làm hỏng nhận dạng
        (
            "đến hết ngày 31/10/2026.",
            "đến hết ngày ba mươi mốt tháng mười năm hai nghìn không trăm hai mươi sáu.",
        ),
        ("hết ngày 5/10, nhanh tay", "hết ngày năm tháng mười, nhanh tay"),
        ("hạn 10/2026.", "hạn tháng mười năm hai nghìn không trăm hai mươi sáu."),
        ("pha 1/2.", "pha một phần hai."),
        ("gọi 0909 123 456.", "gọi không chín không chín một hai ba bốn năm sáu."),
        ("Bấm vào CTA.", "Bấm vào xi ti ây."),
    ],
)
def test_sentence_end_punctuation(text: str, expected: str) -> None:
    assert normalize_vi(text, pronunciations=None) == expected


def test_trial_script_date_sentence() -> None:
    out = normalize_vi("Giá chỉ còn 390.000đ, giảm 25% đến hết ngày 31/10/2026.")
    assert out == (
        "Giá chỉ còn ba trăm chín mươi nghìn đồng, giảm hai mươi lăm phần trăm "
        "đến hết ngày ba mươi mốt tháng mười năm hai nghìn không trăm hai mươi sáu."
    )
    assert "/" not in out


def test_whole_sentence() -> None:
    out = normalize_vi("Bình Lock&Lock 500ml chỉ còn 390.000đ, giảm 25%.")
    assert out == (
        "Bình Lốc en Lốc năm trăm mi li lít chỉ còn ba trăm chín mươi nghìn đồng, "
        "giảm hai mươi lăm phần trăm."
    )


def test_no_digits_left_in_trial_sentences() -> None:
    import json
    from pathlib import Path

    data = json.loads((Path(__file__).parents[2] / "sentences.json").read_text(encoding="utf-8"))
    texts = [(item["id"], item["text"]) for item in data["sentences"]] + [("script", data["script"])]
    for sid, text in texts:
        out = normalize_vi(text)
        assert not any(c.isdigit() for c in out), (sid, out)
        assert "/" not in out, (sid, out)  # ngày/phân số phải được đọc ra chữ, không để dấu /
