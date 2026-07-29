"""EBS katalog parser'ının (scraper.parse_catalog_page) birim testleri — ağa ve DB'ye dokunmaz."""
import os
import sys

import pytest

SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

# scripts/scraper.py dev-only ve .gitignore'da: temiz bir clone'da bulunmaz. Import'u
# koşullu tutmazsak bu dosya collection sırasında patlar ve suite'in tamamını düşürür.
try:
    from scraper import (  # noqa: E402
        CatalogProgram,
        IKINCI_OGRETIM_RE,
        force_turkish,
        parse_catalog_page,
    )
except ModuleNotFoundError:
    pytest.skip(
        "scripts/scraper.py sürüm takibinde değil — katalog parser testleri atlandı",
        allow_module_level=True,
    )


def _row(href: str, text: str) -> str:
    return f'<tr id="r{abs(hash(href + text))}"><td><a href="{href}">{text}</a></td></tr>'


def _view(hidden: bool, rows: str) -> str:
    cls = "rmpView rmpHidden" if hidden else "rmpView"
    return f'<div class="{cls}"><table>{rows}</table></div>'


# Gerçek katalogdan kırpılmış yapı: iki sekme (biri gizli), satır sırasıyla hiyerarşi.
CATALOG_HTML = _view(
    False,
    _row("BirimBilgi.aspx?lng=1&dzy=3&br=100", "MÜHENDİSLİK FAKÜLTESİ")
    + _row("BolumBilgi.aspx?lng=1&dzy=3&br=100&bl=200", "BİLGİSAYAR MÜHENDİSLİĞİ BÖLÜMÜ")
    + _row(
        "Program.aspx?lng=1&dzy=3&br=100&bl=200&pr=1&dm=1&ps=0",
        "253 Bilgisayar Mühendisliği (Aktif)",
    )
    + _row(
        "Program.aspx?lng=1&dzy=3&br=100&bl=200&pr=2&dm=1&ps=0",
        "254 Bilgisayar Mühendisliği (İ.Ö.) (Yarı Pasif)",
    )
    + _row(
        "Program.aspx?lng=1&dzy=3&br=100&bl=200&pr=3&dm=1&ps=0",
        "255 Eski Program (Kapatılmış)",
    )
    + _row("BirimBilgi.aspx?lng=1&dzy=3&br=414", "DENİZLİ SAĞLIK YÜKSEKOKULU")
    + _row("BolumBilgi.aspx?lng=1&dzy=3&br=414&bl=418", "HEMŞİRELİK BÖLÜMÜ")
    + _row("Program.aspx?lng=1&dzy=3&br=414&bl=418&pr=73&dm=1&ps=0", "301 Hemşirelik (Yarı Pasif)"),
) + _view(
    True,
    _row("BirimBilgi.aspx?lng=1&dzy=8&br=8327", "ARKEOLOJİ ENSTİTÜSÜ")
    + _row("BolumBilgi.aspx?lng=1&dzy=8&br=8327&bl=8362", "ARKEOLOJİ ANA BİLİM DALI")
    + _row("Program.aspx?lng=1&dzy=8&br=8327&bl=8362&pr=601&dm=1&ps=0", "2663 Arkeoloji Dr. (Aktif)"),
)


class TestParseCatalogPage:
    def test_tum_dereceler_filtresiz_doner(self):
        programs = parse_catalog_page(CATALOG_HTML)
        assert len(programs) == 5
        # Gizli sekme (rmpHidden) de parse edilir — AJAX yok, HTML'de hazır.
        assert {p.dzy for p in programs} == {"3", "8"}

    def test_dzy_satirin_kendi_hrefinden_okunur(self):
        doktora = parse_catalog_page(CATALOG_HTML, dzy="8")
        assert [p.program_name for p in doktora] == ["Arkeoloji Dr."]
        assert doktora[0].dzy == "8"

    def test_satir_sirasi_hiyerarsiyi_belirler(self):
        programs = parse_catalog_page(CATALOG_HTML, dzy="3")
        by_name = {p.program_name: p for p in programs}
        hemsirelik = by_name["Hemşirelik"]
        assert hemsirelik.unit_name == "DENİZLİ SAĞLIK YÜKSEKOKULU"
        assert hemsirelik.unit_br == "414"
        assert hemsirelik.dept_name == "HEMŞİRELİK BÖLÜMÜ"
        assert hemsirelik.dept_bl == "418"
        # Bir sonraki birime geçildiğinde önceki bölüm sızmamalı
        assert by_name["Bilgisayar Mühendisliği"].dept_bl == "200"

    def test_program_satiri_kod_ad_durum_ayrimi(self):
        program = parse_catalog_page(CATALOG_HTML, dzy="3")[0]
        assert (program.program_code, program.program_name, program.status) == (
            "253",
            "Bilgisayar Mühendisliği",
            "Aktif",
        )

    def test_durum_filtresi(self):
        programs = parse_catalog_page(CATALOG_HTML, dzy="3", statuses=["Aktif", "Yarı Pasif"])
        assert len(programs) == 3
        assert "Eski Program" not in {p.program_name for p in programs}

    def test_program_url_mutlaklastirilir(self):
        program = parse_catalog_page(CATALOG_HTML, dzy="3")[0]
        assert program.program_url.startswith(
            "https://ebs.pusula.pau.edu.tr/BilgiGoster/Program.aspx?"
        )
        assert "bl=200" in program.program_url

    def test_rmpview_yoksa_tum_belge_taranir(self):
        html = "<table>" + _row(
            "Program.aspx?lng=1&dzy=3&br=1&bl=2&pr=3&dm=1&ps=0", "10 Tıp Doktorluğu (Aktif)"
        ) + "</table>"
        assert [p.program_name for p in parse_catalog_page(html)] == ["Tıp Doktorluğu"]

    def test_ingilizce_program_linki_turkceye_cevrilir(self):
        html = "<table>" + _row(
            "Program.aspx?lng=2&dzy=3&br=19&bl=51&pr=24&dm=1&ps=0", "131 İngilizce Öğretmenliği (Aktif)"
        ) + "</table>"
        program = parse_catalog_page(html)[0]
        assert "lng=1" in program.program_url
        assert "lng=2" not in program.program_url


class TestForceTurkish:
    @pytest.mark.parametrize("url, expected", [
        ("https://x/Program.aspx?lng=2&dzy=3", "https://x/Program.aspx?lng=1&dzy=3"),
        ("https://x/Ders.aspx?dzy=3&lng=2&dk=1", "https://x/Ders.aspx?dzy=3&lng=1&dk=1"),
        ("https://x/Program.aspx?lng=1&dzy=3", "https://x/Program.aspx?lng=1&dzy=3"),
        ("https://x/Program.aspx?dzy=3", "https://x/Program.aspx?dzy=3"),
    ])
    def test_lng_parametresi_normalize_edilir(self, url, expected):
        assert force_turkish(url) == expected


class TestIkinciOgretim:
    @pytest.mark.parametrize(
        "name, base",
        [
            ("Bilgisayar Mühendisliği (İ.Ö.)", "Bilgisayar Mühendisliği"),
            ("Bilgisayar Mühendisliği (İ.Ö)", "Bilgisayar Mühendisliği"),
            ("İlahiyat (M.T.O.K) (İ.Ö.)", "İlahiyat (M.T.O.K)"),
            ("Hemşirelik ( İ.Ö. )", "Hemşirelik"),
        ],
    )
    def test_ikinci_ogretim_eki_soyulur(self, name, base):
        program = CatalogProgram("3", "", "", "", "", "1", name, "Aktif", "")
        assert program.is_ikinci_ogretim is True
        assert program.base_program_name == base

    @pytest.mark.parametrize(
        "name",
        ["Bilgisayar Mühendisliği", "İlahiyat (M.T.O.K.)", "İngiliz Dili ve Edebiyatı (İngilizce)"],
    )
    def test_normal_program_ikinci_ogretim_degil(self, name):
        program = CatalogProgram("3", "", "", "", "", "1", name, "Aktif", "")
        assert program.is_ikinci_ogretim is False
        assert program.base_program_name == name

    def test_ek_sadece_sonda_eslesir(self):
        assert IKINCI_OGRETIM_RE.search("(İ.Ö.) Bilgisayar") is None
