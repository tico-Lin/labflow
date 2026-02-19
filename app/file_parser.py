"""
文件解析器 - 支援多種科學數據格式的簡單解析

支持的格式：
- XRD: .xy, .xye, .txt (含 metadata)
- CIF: 晶體結構檔案
- CSV: 電化學數據
- 儀器設置: .instprm
- 項目檔案: .ipj

【使用方式】
parser = FileParser(file_path)
metadata = parser.extract_metadata()
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List


class FileParser:
    """通用文件解析器，自動檢測並解析file_type"""

    SUPPORTED_FORMATS = {
        ".xy": "XRD",
        ".xye": "XRD",
        ".cif": "CIF",
        ".csv": "CSV",
        ".txt": "TXT",
        ".instprm": "INSTPRM",
        ".ipj": "IPJ",
        ".tif": "IMAGE",
        ".docx": "DOCUMENT",
    }

    def __init__(self, file_path: str):
        """初始化解析器

        Args:
            file_path: 要解析的文件路徑
        """
        self.file_path = Path(file_path)
        self.file_name = self.file_path.name
        self.file_ext = self.file_path.suffix.lower()
        self.fmt = self._detect_format()

    def _detect_format(self) -> str:
        """檢測文件格式"""
        # 首先支持已知擴展名的優先
        if self.file_ext in self.SUPPORTED_FORMATS:
            # 如果副檔名看起來通用（如 .txt），則查看檔名內容
            if self.file_ext == ".txt":
                # 檢查檔名中是否有特定的數據類型指示
                filename_upper = self.file_name.upper()
                if "XRD" in filename_upper or "_XY" in filename_upper:
                    return "XRD"
                if "EIS" in filename_upper:
                    return "EIS"
                if "CV" in filename_upper:
                    return "CV"
                if "PDF" in filename_upper:  # JCPDS PDF 檔案
                    return "PDF"

                # 檢查文件內容前幾行以確定格式
                try:
                    with open(
                        self.file_path, "r", encoding="utf-8", errors="ignore"
                    ) as f:
                        first_lines = f.read(500).upper()  # 讀取前 500 個字符
                        if (
                            "XRD" in first_lines
                            or "2-THETA" in first_lines
                            or "INTENSITY" in first_lines
                        ):
                            return "XRD"
                        if "EIS" in first_lines or "频率" in first_lines.replace(
                            "FREQUENCY", ""
                        ):
                            return "EIS"
                except Exception:
                    pass

            return self.SUPPORTED_FORMATS[self.file_ext]

        # 根據檔名推測（只有當副檔名為通用時）
        filename_upper = self.file_name.upper()
        if "XRD" in filename_upper:
            return "XRD"
        if "EIS" in filename_upper:
            return "EIS"
        if "CV" in filename_upper:
            return "CV"
        if "SEM" in filename_upper:
            return "SEM"
        if "EDS" in filename_upper:
            return "EDS"

        return "UNKNOWN"

    def extract_metadata(self) -> Dict[str, Any]:
        """提取文件元數據

        Returns:
            包含檔案元數據的字典
        """
        metadata = {
            "filename": self.file_name,
            "format": self.fmt,
            "file_type": self.fmt,
            "path": str(self.file_path),
            "size": self.file_path.stat().st_size if self.file_path.exists() else 0,
            "extracted_fields": {},
        }

        # 根據格式調用相應的提取器
        if self.fmt == "XRD":
            metadata["extracted_fields"] = self._parse_xrd()
        elif self.fmt == "CIF":
            metadata["extracted_fields"] = self._parse_cif()
        elif self.fmt == "CSV":
            metadata["extracted_fields"] = self._parse_csv()
        elif self.fmt == "INSTPRM":
            metadata["extracted_fields"] = self._parse_instprm()

        # 從檔名提取日期和樣品信息
        self._extract_filename_info(metadata)

        return metadata

    def _extract_filename_info(self, metadata: Dict) -> None:
        """從檔名中提取日期和樣品信息"""
        filename = self.file_name

        # 提取日期（YYYYMMDD 格式）
        date_pattern = r"(\d{8}|\d{4}-\d{2}-\d{2}|\d{4}/\d{2}/\d{2})"
        date_match = re.search(date_pattern, filename)
        if date_match:
            metadata["extracted_fields"]["date"] = date_match.group(0)

        # 提取樣品編號或名稱
        # 例如: Cr3_XRD_20250104 -> Cr3
        sample_pattern = r"^([A-Za-z0-9_]+?)[\s_-]"
        sample_match = re.match(sample_pattern, filename)
        if sample_match:
            metadata["extracted_fields"]["sample_id"] = sample_match.group(1)

        # 提取儀器信息（例如 TPS19A, MYTHEN）
        instrument_pattern = r"(TPS19A|MYTHEN|Newport|Delta|Rigaku)"
        instr_match = re.search(instrument_pattern, filename, re.IGNORECASE)
        if instr_match:
            metadata["extracted_fields"]["instrument"] = instr_match.group(1)

    def _parse_xrd(self) -> Dict[str, Any]:
        """解析 XRD 數據文件"""
        fields = {"format": "XRD Diffraction Data"}

        if not self.file_path.exists():
            return fields

        try:
            with open(self.file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

                # 計算數據點
                data_lines = [l for l in lines if l.strip() and not l.startswith("#")]
                fields["data_points"] = len(data_lines)

                # 提取頭部註釋
                header_lines = [l for l in lines[:20] if l.startswith("#")]
                if header_lines:
                    fields["header"] = "\n".join(header_lines[:5])

                # 檢查是否為標準格式（2θ, Intensity）
                if len(data_lines) > 0:
                    first_data = data_lines[0]
                    try:
                        parts = first_data.split()
                        if len(parts) >= 2:
                            two_theta = float(parts[0])
                            intensity = float(parts[1])
                            fields["two_theta_range"] = f"{two_theta:.1f}°"
                            fields["has_intensity"] = True
                    except ValueError:
                        pass
        except Exception as e:
            fields["parse_error"] = str(e)

        return fields

    def _parse_cif(self) -> Dict[str, Any]:
        """解析 CIF（晶體信息）文件"""
        fields = {"format": "Crystallographic Information File"}

        if not self.file_path.exists():
            return fields

        try:
            with open(self.file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

                # 提取化學式
                formula_match = re.search(
                    r"_chemical_formula_\w+\s+([A-Za-z0-9\s\-\(\)]+)", content
                )
                if formula_match:
                    fields["chemical_formula"] = formula_match.group(1).strip()

                # 提取晶體系統
                system_match = re.search(r"_symmetry_cell_setting\s+(\w+)", content)
                if system_match:
                    fields["crystal_system"] = system_match.group(1)

                # 提取空間群
                space_group_match = re.search(
                    r"_symmetry_space_group_name_H-M\s+['\"]?([^'\"]+)['\"]?", content
                )
                if space_group_match:
                    fields["space_group"] = space_group_match.group(1)

                fields["line_count"] = len(content.split("\n"))
        except Exception as e:
            fields["parse_error"] = str(e)

        return fields

    def _parse_csv(self) -> Dict[str, Any]:
        """解析 CSV 文件"""
        fields = {"format": "Comma-Separated Values"}

        if not self.file_path.exists():
            return fields

        try:
            with open(self.file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                fields["line_count"] = len(lines)

                if len(lines) > 0:
                    # 推測欄位
                    header = lines[0]
                    fields["columns"] = [c.strip() for c in header.split(",")]
                    fields["column_count"] = len(fields["columns"])

                    # 檢查是否為電化學數據（CV, EIS）
                    header_lower = header.lower()
                    if "voltage" in header_lower or "potential" in header_lower:
                        fields["data_type"] = "Electrochemistry"
                    if "current" in header_lower:
                        fields["has_current"] = True
                    if "impedance" in header_lower or "resistance" in header_lower:
                        fields["data_type"] = "Impedance"
        except Exception as e:
            fields["parse_error"] = str(e)

        return fields

    def _parse_instprm(self) -> Dict[str, Any]:
        """解析儀器設置文件"""
        fields = {"format": "Instrument Parameter File"}

        if not self.file_path.exists():
            return fields

        try:
            with open(self.file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

                # 提取儀器名稱
                instr_match = re.search(
                    r"Instrument\s*=\s*(.+?)(?:\n|$)", content, re.IGNORECASE
                )
                if instr_match:
                    fields["instrument_name"] = instr_match.group(1).strip()

                # 提取波長
                wavelength_match = re.search(
                    r"Wavelength\s*=\s*([0-9.]+)", content, re.IGNORECASE
                )
                if wavelength_match:
                    fields["wavelength"] = f"{wavelength_match.group(1)} Å"

                # 提取溫度
                temp_match = re.search(
                    r"Temperature\s*=\s*([0-9.]+)", content, re.IGNORECASE
                )
                if temp_match:
                    fields["temperature"] = f"{temp_match.group(1)} K"

                fields["line_count"] = len(content.split("\n"))
        except Exception as e:
            fields["parse_error"] = str(e)

        return fields

    def get_file_type(self) -> str:
        """獲取檔案類型"""
        return self.fmt

    def get_suggested_tags(self) -> List[str]:
        """建議標籤"""
        tags = [self.fmt]

        # 根據檔名添加標籤
        if "XRD" in self.file_name.upper():
            tags.extend(["X-ray衍射", "結構分析"])
        if "CIF" in self.file_name.upper():
            tags.extend(["晶體結構", "結構檔案"])
        if "EIS" in self.file_name.upper():
            tags.extend(["阻抗譜", "電化學"])
        if "CV" in self.file_name.upper():
            tags.extend(["循環伏安法", "電化學"])
        if "SEM" in self.file_name.upper():
            tags.extend(["掃描電顯", "顯微鏡"])
        if "EDS" in self.file_name.upper():
            tags.extend(["能量色散X射線", "成分分析"])

        # 根據樣品名稱添加標籤
        if "MnO2" in self.file_name or "Mn" in self.file_name:
            tags.extend(["MnO2", "錳基氧化物"])
        if "NMO" in self.file_name:
            tags.extend(["NMO", "層狀鐵電材料"])
        if "Cr" in self.file_name:
            tags.extend(["鉻摻雜", "Cr-doped"])

        # 移除重複
        return list(set(tags))


if __name__ == "__main__":
    # 測試示例
    import sys

    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        parser = FileParser(file_path)
        print(f"文件: {parser.file_name}")
        print(f"格式: {parser.get_file_type()}")
        print(
            f"元數據: {json.dumps(parser.extract_metadata(), indent=2, ensure_ascii=False)}"
        )
        print(f"建議標籤: {parser.get_suggested_tags()}")
