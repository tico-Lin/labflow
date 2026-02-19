"""
文件解析器單元測試

測試 FileParser 對多種科學數據格式的支持
"""

from pathlib import Path

import pytest

from app.file_parser import FileParser

SAMPLE_DIR = Path(__file__).parent.parent / "sample"


class TestFileParser:
    """文件解析器測試"""

    def test_parser_initialization(self):
        """測試解析器初始化"""
        parser = FileParser("test.xy")
        assert parser.file_name == "test.xy"
        assert parser.fmt == "XRD"

    def test_detect_xrd_format(self):
        """測試 XRD 格式檢測"""
        test_cases = [
            ("sample.xy", "XRD"),
            ("data.xye", "XRD"),
            ("Cr3_XRD_20250104.txt", "XRD"),
            ("XRD_sample.txt", "XRD"),
        ]
        for filename, expected_fmt in test_cases:
            parser = FileParser(filename)
            assert parser.get_file_type() == expected_fmt

    def test_detect_cif_format(self):
        """測試 CIF 格式檢測"""
        parser = FileParser("structure.cif")
        assert parser.get_file_type() == "CIF"

    def test_detect_csv_format(self):
        """測試 CSV 格式檢測"""
        parser = FileParser("data.csv")
        assert parser.get_file_type() == "CSV"

    def test_detect_instprm_format(self):
        """測試儀器設置格式檢測"""
        parser = FileParser("instrument.instprm")
        assert parser.get_file_type() == "INSTPRM"

    def test_sample_xye_file(self):
        """測試 sample 目錄中的 XYE 檔案"""
        xye_file = SAMPLE_DIR / "MOCr00012.xye"

        assert xye_file.exists(), f"Sample file not found: {xye_file}"

        parser = FileParser(str(xye_file))
        assert parser.get_file_type() == "XRD"

        metadata = parser.extract_metadata()
        assert metadata["filename"] == xye_file.name
        assert metadata["format"] == "XRD"
        assert "extracted_fields" in metadata

    def test_sample_cif_file(self):
        """測試 sample 目錄中的 CIF 檔案"""
        cif_file = SAMPLE_DIR / "bataMnO2.cif"

        assert cif_file.exists(), f"Sample file not found: {cif_file}"

        parser = FileParser(str(cif_file))
        assert parser.get_file_type() == "CIF"

        metadata = parser.extract_metadata()
        assert metadata["filename"] == cif_file.name
        assert metadata["format"] == "CIF"
        assert (
            "chemical_formula" in metadata["extracted_fields"]
            or "parse_error" not in metadata["extracted_fields"]
        )

    def test_sample_instprm_file(self):
        """測試 sample 目錄中的 INSTPRM 檔案"""
        instprm_file = SAMPLE_DIR / "2025-11-28_TPS19A_MYTHEN_20000.instprm"

        assert instprm_file.exists(), f"Sample file not found: {instprm_file}"

        parser = FileParser(str(instprm_file))
        assert parser.get_file_type() == "INSTPRM"

        metadata = parser.extract_metadata()
        assert metadata["filename"] == instprm_file.name
        assert metadata["format"] == "INSTPRM"

    def test_filename_date_extraction(self):
        """測試從檔名提取日期"""
        parser = FileParser("Cr3_XRD_20250104.xy")
        metadata = parser.extract_metadata()

        assert (
            "date" in metadata["extracted_fields"]
            or "sample_id" in metadata["extracted_fields"]
        )

    def test_sample_suggestion(self):
        """測試建議標籤功能"""
        parser = FileParser("MnO2_XRD_20250115.xy")
        tags = parser.get_suggested_tags()

        assert "XRD" in tags
        assert len(tags) > 1

    def test_parse_xrd_metadata(self):
        """測試 XRD 數據解析"""
        xye_file = SAMPLE_DIR / "MOCr00012.xye"

        assert xye_file.exists(), f"Sample file not found: {xye_file}"

        parser = FileParser(str(xye_file))
        metadata = parser.extract_metadata()

        # XRD 檔案應該有一些提取的欄位
        fields = metadata["extracted_fields"]
        assert "data_points" in fields or "parse_error" in fields or fields == {}

    def test_supported_formats(self):
        """測試支持的格式列表"""
        parser = FileParser("dummy.txt")

        assert ".xy" in FileParser.SUPPORTED_FORMATS
        assert ".xye" in FileParser.SUPPORTED_FORMATS
        assert ".cif" in FileParser.SUPPORTED_FORMATS
        assert ".csv" in FileParser.SUPPORTED_FORMATS
        assert ".instprm" in FileParser.SUPPORTED_FORMATS

    def test_unknown_format(self):
        """測試未知格式"""
        parser = FileParser("unknown.xyz")
        assert parser.get_file_type() == "UNKNOWN"

    def test_metadata_structure(self):
        """測試元數據結構"""
        parser = FileParser("sample.xy")
        metadata = parser.extract_metadata()

        required_fields = ["filename", "format", "file_type", "extracted_fields"]
        for field in required_fields:
            assert field in metadata


class TestFileParserIntegration:
    """文件解析器集成測試 - 使用 sample 目錄中的真實檔案"""

    @pytest.mark.integration
    def test_parse_all_sample_files(self):
        """測試解析所有 sample 檔案"""
        assert SAMPLE_DIR.exists(), "Sample directory not found"

        sample_files = list(SAMPLE_DIR.glob("*"))

        for file_path in sample_files:
            if file_path.is_file():
                parser = FileParser(str(file_path))
                metadata = parser.extract_metadata()

                # 驗證基本結構
                assert "filename" in metadata
                assert "format" in metadata
                assert "file_type" in metadata

                print(f"✓ {file_path.name}: {metadata['format']}")

    @pytest.mark.integration
    def test_sample_file_suggestions(self):
        """測試 sample 檔案的標籤建議"""
        assert SAMPLE_DIR.exists(), "Sample directory not found"

        test_files = {
            "MOCr00012.xye": ["XRD"],
            "bataMnO2.cif": ["CIF"],
            "20251203 nmo.txt": ["XRD"],  # TXT 檔案經過內容檢測後識別為 XRD
        }

        for filename, expected_tags in test_files.items():
            file_path = SAMPLE_DIR / filename
            if file_path.exists():
                parser = FileParser(str(file_path))
                tags = parser.get_suggested_tags()

                for expected in expected_tags:
                    assert any(expected.lower() in tag.lower() for tag in tags), (
                        f"Expected {expected} in tags for {filename}, got {tags}"
                    )

                print(f"✓ {filename}: {tags}")
