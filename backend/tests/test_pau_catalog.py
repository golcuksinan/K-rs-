"""EBS parser'larının (katalog + ders planı) birim testleri — ağa ve DB'ye dokunmaz."""
import os
import sys

import pytest

SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

# scripts/scraper.py dev-only ve .gitignore'da: temiz bir clone'da bulunmaz. Import'u
# koşullu tutmazsak bu dosya collection sırasında patlar ve suite'in tamamını düşürür.
try:
    from scraper import (  # noqa: E402
        CatalogProgram,
        IKINCI_OGRETIM_RE,
        _baslik_semesters,
        force_turkish,
        parse_catalog_page,
        parse_program_page,
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


def _plan_row(code: str, name: str, tur: str, dk: str = "1", lng: str = "1") -> str:
    link = f'<a href="Ders.aspx?lng={lng}&amp;dk={dk}&amp;ds=0">{name}</a>' if dk else name
    return f"<tr><td>{code}</td><td>{link}</td><td>3+0</td><td>5</td><td>{tur}</td></tr>"


_PLAN_HEADER = (
    "<tr><th>Ders Kodu</th><th>Ders Adı</th><th>T+U</th><th>AKTS</th><th>Ders Türü</th></tr>"
)


def _plan_table(rows: str) -> str:
    return f"<table>{_PLAN_HEADER}{rows}</table>"


class TestBaslikSemesters:
    """Yarıyıl tablonun içinde değil, tablodan ÖNCEKİ başlık metninde yazıyor."""

    @pytest.mark.parametrize(
        "text, expected",
        [
            ("3. Yarıyıl Ders Planı", {3}),
            ("5. Yarıyıl Seçmeli Grupları : Alan Eğitimi Seçmeli 3", {5}),
            ("2 . Yıl Ders Planı", {3, 4}),
            ("1 . Yıl Ders Planı", {1, 2}),
        ],
    )
    def test_yariyil_ve_yil_bicimleri(self, text, expected):
        assert _baslik_semesters(text) == expected

    def test_yil_ve_yariyil_bir_aradaysa_yariyil_kazanir(self):
        """Yıl bazlı programda başlık ikisini birden taşıyabiliyor; yarıyıl daha kesin."""
        assert _baslik_semesters("1. Yıl Seçmeli Grupları : 2. Yarıyıl (Bahar) Seçmeli") == {2}

    def test_plan_basligi_olmayan_metin_none_doner(self):
        """None = durum korunur; boş küme = başlık ama sayı okunamadı, önceki DEVRALINMAZ."""
        assert _baslik_semesters("Ders Şubeleri") is None

    def test_sayisiz_baslik_bos_kume_doner(self):
        assert _baslik_semesters("Ders Planı") == set()


class TestParseProgramPage:
    def test_yariyil_onceki_basliktan_okunur(self):
        html = "<h3>1. Yarıyıl Ders Planı</h3>" + _plan_table(
            _plan_row("MAT 101", "MATEMATİK I", "Zorunlu")
        )
        (course,) = parse_program_page(html, base_url="https://x/Program.aspx")
        assert course.semesters == {1}
        assert course.is_elective is False

    def test_ders_turu_baslik_sutunundan_okunur(self):
        html = "<h3>3. Yarıyıl Seçmeli Grupları : Alan Seçmeli</h3>" + _plan_table(
            _plan_row("ING 205", "İNGİLİZCE", "Seçmeli")
        )
        (course,) = parse_program_page(html, base_url="https://x/Program.aspx")
        assert course.is_elective is True

    def test_bilinmeyen_tur_none_kalir(self):
        html = "<h3>1. Yarıyıl Ders Planı</h3>" + _plan_table(_plan_row("MAT 101", "MAT", ""))
        (course,) = parse_program_page(html, base_url="https://x/Program.aspx")
        assert course.is_elective is None

    def test_ayni_ders_birden_cok_yariyilda_tek_satir_olur(self):
        """Seçmeli havuzu birden çok yarıyılda listeleniyor → kod bazlı dedupe, yarıyıl union."""
        html = (
            "<h3>3. Yarıyıl Seçmeli Grupları : Alan Seçmeli</h3>"
            + _plan_table(_plan_row("ING 205", "İNGİLİZCE", "Seçmeli"))
            + "<h3>5. Yarıyıl Seçmeli Grupları : Alan Seçmeli 2</h3>"
            + _plan_table(_plan_row("ING 205", "İNGİLİZCE", "Seçmeli"))
        )
        (course,) = parse_program_page(html, base_url="https://x/Program.aspx")
        assert course.semesters == {3, 5}

    def test_cakismada_zorunlu_kazanir(self):
        """IENG 104 gerçek vakası: 2. yarıyılda zorunlu, sonraki yarıyıllarda seçmeli listeli."""
        html = (
            "<h3>2. Yarıyıl Ders Planı</h3>"
            + _plan_table(_plan_row("IENG 104", "GENEL EKONOMİ", "Zorunlu"))
            + "<h3>5. Yarıyıl Ders Planı</h3>"
            + _plan_table(_plan_row("IENG 104", "GENEL EKONOMİ", "Seçmeli"))
        )
        (course,) = parse_program_page(html, base_url="https://x/Program.aspx")
        assert course.is_elective is False
        assert course.semesters == {2, 5}

    def test_sarmalayici_tablo_sayilmaz(self):
        """En dıştaki tablo bütün yarıyılları tek tabloymuş gibi kapsıyor; sayılırsa
        yalnızca orada geçen satırlar yanlış yarıyılla girer."""
        leaf = _plan_table(_plan_row("MAT 101", "MATEMATİK I", "Zorunlu"))
        html = (
            "<h3>1. Yarıyıl Ders Planı</h3>"
            f"<table>{_PLAN_HEADER}"
            f'{_plan_row("SRM 999", "YALNIZCA SARMALAYICIDA", "Zorunlu", dk="42")}'
            f"<tr><td>{leaf}</td></tr></table>"
        )
        codes = {c.code for c in parse_program_page(html, base_url="https://x/Program.aspx")}
        assert codes == {"MAT 101"}

    def test_somut_kodu_olmayan_slot_atlanir(self):
        html = "<h3>1. Yarıyıl Ders Planı</h3>" + _plan_table(
            _plan_row("-", "İsteğe Bağlı Seçmeli-1", "Seçmeli")
        )
        assert parse_program_page(html, base_url="https://x/Program.aspx") == []

    def test_linksiz_satir_atlanir(self):
        html = "<h3>1. Yarıyıl Ders Planı</h3>" + _plan_table(
            _plan_row("FIZ 101", "FİZİK I", "Zorunlu", dk="")
        )
        assert parse_program_page(html, base_url="https://x/Program.aspx") == []

    def test_ders_detay_linki_turkceye_normalize_edilir(self):
        html = "<h3>1. Yarıyıl Ders Planı</h3>" + _plan_table(
            _plan_row("MAT 101", "MATEMATİK I", "Zorunlu", lng="2")
        )
        (course,) = parse_program_page(html, base_url="https://x/Program.aspx")
        assert "lng=1" in course.detail_url and "lng=2" not in course.detail_url

    def test_ders_plani_olmayan_sayfa_bos_doner(self):
        assert parse_program_page("<h1>Program</h1><table><tr><th>Başka</th></tr></table>", "u") == []
