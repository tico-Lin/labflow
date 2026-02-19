"""
檔案自動分類服務 (File Classification Service)

功能：
- 根據檔案名稱和擴展名自動識別檔案類型
- 提取元數據（樣品名、儀器類型、日期等）
- 自動建議標籤

支援的檔案類型：
- XRD: X-ray Diffraction (.xy, .txt, .xrdml, .raw)
- SEM: Scanning Electron Microscopy (.tif, .tiff, .jpg, .jpeg, .png, .bmp)
- EIS: Electrochemical Impedance Spectroscopy (.txt, .csv, .xlsx)
- CV: Cyclic Voltammetry (.txt, .csv, .xlsx)
- Excel: 實驗記錄 (.xlsx, .xls)
- 圖片: 通用圖片檔案
- 數據: 通用數據檔案

命名規範範例：
- Cr3_XRD_20250104.xy → {sample: "Cr3", type: "XRD", date: "2025-01-04"}
- Sample_A_SEM_2025-01-15_01.tif → {sample: "Sample_A", type: "SEM", date: "2025-01-15", sequence: "01"}
- EIS_MnO2_20250110.txt → {type: "EIS", sample: "MnO2", date: "2025-01-10"}

作者：GitHub Copilot
創建日期：2026-02-17
"""

from __future__ import annotations
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    """分類結果"""
    file_type: str  # 檔案類型：XRD, SEM, EIS, CV, Excel, Image, Data, Unknown
    confidence: float  # 置信度 (0.0-1.0)
    suggested_tags: List[str]  # 建議的標籤
    metadata: Dict[str, Any]  # 提取的元數據
    source: str = "auto"  # 分類來源：auto, manual


class FileClassificationService:
    """檔案自動分類服務"""
    
    # 檔案類型與擴展名映射
    FILE_TYPE_EXTENSIONS = {
        "XRD": [".xy", ".txt", ".xrdml", ".raw", ".brml", ".cif"],
        "SEM": [".tif", ".tiff", ".jpg", ".jpeg", ".png", ".bmp", ".dm3", ".dm4"],
        "TEM": [".tif", ".tiff", ".dm3", ".dm4"],
        "EIS": [".txt", ".csv", ".xlsx", ".mpt", ".mpr"],
        "CV": [".txt", ".csv", ".xlsx", ".mpt", ".mpr"],
        "Excel": [".xlsx", ".xls"],
        "Image": [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff"],
        "Data": [".txt", ".csv", ".dat", ".asc"],
        "PDF": [".pdf"],
        "Word": [".docx", ".doc"],
    }
    
    # 關鍵字映射 (檔名中包含這些關鍵字時的類型推斷)
    KEYWORD_PATTERNS = {
        "XRD": [r"xrd", r"diffraction", r"x-ray", r"powder"],
        "SEM": [r"sem", r"scanning.*electron", r"morphology"],
        "TEM": [r"tem", r"transmission.*electron"],
        "EIS": [r"eis", r"impedance", r"nyquist", r"bode"],
        "CV": [r"cv", r"cyclic.*voltammetry", r"voltammetry"],
        "BET": [r"bet", r"surface.*area", r"adsorption"],
        "XPS": [r"xps", r"photoelectron", r"esca"],
        "FTIR": [r"ftir", r"infrared", r"ir"],
        "Raman": [r"raman", r"spectroscopy"],
        "Battery": [r"battery", r"cell", r"charge", r"discharge", r"capacity"],
        "Synthesis": [r"synthesis", r"preparation", r"synth"],
    }
    
    # 日期格式正則表達式
    DATE_PATTERNS = [
        r"(\d{4})[-_]?(\d{2})[-_]?(\d{2})",  # YYYYMMDD, YYYY-MM-DD, YYYY_MM_DD
        r"(\d{2})[-_]?(\d{2})[-_]?(\d{4})",  # DDMMYYYY, DD-MM-YYYY, DD_MM_YYYY
        r"(\d{4})(\d{2})(\d{2})",            # YYYYMMDD 連續
    ]
    
    def __init__(self):
        """初始化分類服務"""
        self.logger = logging.getLogger(__name__)
    
    def classify_file(self, filename: str, content: Optional[bytes] = None) -> ClassificationResult:
        """
        分類單個檔案
        
        Args:
            filename: 檔案名稱
            content: 檔案內容（可選，用於更精確的分類）
        
        Returns:
            ClassificationResult: 分類結果
        """
        path = Path(filename)
        extension = path.suffix.lower()
        basename = path.stem
        
        # 1. 提取元數據
        metadata = self._extract_metadata(filename)
        
        # 2. 根據擴展名判斷類型
        file_type_by_ext, confidence_ext = self._classify_by_extension(extension)
        
        # 3. 根據檔名關鍵字判斷類型
        file_type_by_keyword, confidence_keyword = self._classify_by_keywords(basename)
        
        # 4. 結合兩種方法選擇最佳結果
        if confidence_keyword > confidence_ext:
            file_type = file_type_by_keyword
            confidence = confidence_keyword
        else:
            file_type = file_type_by_ext
            confidence = confidence_ext
        
        # 5. 如果有內容，可以進一步分析（未來擴展）
        if content:
            # TODO: 分析檔案內容進行更精確的分類
            pass
        
        # 6. 生成建議標籤
        suggested_tags = self._generate_tags(file_type, metadata, basename)
        
        self.logger.info(
            f"檔案分類完成: {filename} -> {file_type} (confidence: {confidence:.2f})"
        )
        
        return ClassificationResult(
            file_type=file_type,
            confidence=confidence,
            suggested_tags=suggested_tags,
            metadata=metadata,
            source="auto"
        )
    
    def _classify_by_extension(self, extension: str) -> Tuple[str, float]:
        """根據擴展名分類"""
        for file_type, extensions in self.FILE_TYPE_EXTENSIONS.items():
            if extension in extensions:
                # 擴展名匹配，高置信度
                return file_type, 0.8
        
        # 未知擴展名
        return "Unknown", 0.1
    
    def _classify_by_keywords(self, basename: str) -> Tuple[str, float]:
        """根據檔名關鍵字分類"""
        basename_lower = basename.lower()
        
        matches = []
        for file_type, patterns in self.KEYWORD_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, basename_lower):
                    matches.append(file_type)
                    break
        
        if matches:
            # 關鍵字匹配，非常高置信度
            return matches[0], 0.95
        
        return "Unknown", 0.0
    
    def _extract_metadata(self, filename: str) -> Dict[str, Any]:
        """
        從檔名提取元數據
        
        支援的格式：
        - Cr3_XRD_20250104.xy
        - Sample_A_SEM_2025-01-15_01.tif
        - EIS_MnO2_20250110.txt
        - MnO2-Cr3-beta_XRD.xy
        """
        metadata = {}
        basename = Path(filename).stem
        
        # 1. 提取日期
        date = self._extract_date(basename)
        if date:
            metadata["date"] = date
        
        # 2. 提取樣品名稱（假設是第一個部分或包含特定模式）
        sample = self._extract_sample_name(basename)
        if sample:
            metadata["sample"] = sample
        
        # 3. 提取序號
        sequence = self._extract_sequence(basename)
        if sequence:
            metadata["sequence"] = sequence
        
        # 4. 提取儀器類型（從關鍵字）
        instrument = self._extract_instrument_type(basename)
        if instrument:
            metadata["instrument"] = instrument
        
        # 5. 其他可能的元數據
        # 檢查是否包含溫度信息
        temp_match = re.search(r"(\d+)C", basename, re.IGNORECASE)
        if temp_match:
            metadata["temperature"] = f"{temp_match.group(1)}°C"
        
        # 檢查是否包含樣品編號
        sample_id_match = re.search(r"S(\d+)", basename, re.IGNORECASE)
        if sample_id_match:
            metadata["sample_id"] = sample_id_match.group(1)
        
        return metadata
    
    def _extract_date(self, basename: str) -> Optional[str]:
        """提取日期"""
        for pattern in self.DATE_PATTERNS:
            match = re.search(pattern, basename)
            if match:
                groups = match.groups()
                try:
                    # 嘗試解析為日期
                    if len(groups[0]) == 4:  # YYYY-MM-DD 格式
                        year, month, day = groups[0], groups[1], groups[2]
                    else:  # DD-MM-YYYY 格式
                        day, month, year = groups[0], groups[1], groups[2]
                    
                    date_obj = datetime(int(year), int(month), int(day))
                    return date_obj.strftime("%Y-%m-%d")
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _extract_sample_name(self, basename: str) -> Optional[str]:
        """
        提取樣品名稱
        
        規則：
        - 如果檔名以 Sample_ 開頭，提取 Sample_XXX
        - 如果檔名格式為 XXX_YYY_..., 提取第一個部分
        - 檢查常見的樣品名稱模式
        - 優先提取化合物名稱（包含數字的大寫字母組合）
        """
        # 模式1: Sample_XXX
        sample_match = re.match(r"(Sample[_-]?\w+)", basename, re.IGNORECASE)
        if sample_match:
            return sample_match.group(1)
        
        # 模式2: XXX_YYY 格式，優先提取第二個部分（如果第一個是儀器類型）
        parts = re.split(r"[_-]", basename)
        if len(parts) >= 2:
            first_part = parts[0]
            second_part = parts[1]
            
            # 檢查第一個部分是否是儀器類型關鍵字
            is_first_instrument = any(
                re.search(pattern, first_part.lower())
                for patterns in self.KEYWORD_PATTERNS.values()
                for pattern in patterns
            )
            
            # 如果第一個是儀器類型，嘗試使用第二個部分
            if is_first_instrument and second_part:
                # 檢查第二個部分是否不是日期
                if not re.match(r"\d{4}[-_]?\d{2}[-_]?\d{2}", second_part) and not re.match(r"\d{8}", second_part):
                    # 優先選擇包含數字的化合物名稱
                    if re.search(r"[A-Z][a-z]?\d+", second_part):
                        return second_part
                    # 否則也接受純字母的樣品名
                    return second_part
            
            # 如果第一個不是儀器類型，檢查它是否像化合物名稱
            if not is_first_instrument and first_part:
                # 優先選擇包含數字的化合物名稱
                if re.search(r"[A-Z][a-z]?\d+", first_part):
                    return first_part
                # 否則也返回第一個部分
                return first_part
        
        # 模式3: 化合物名稱搜索（作為後備）
        # 查找包含數字的化合物名稱 (例如: MnO2, Cr3, LiFePO4)
        compound_matches = re.findall(r"([A-Z][a-z]?\d+(?:[A-Z][a-z]?\d*)*)", basename)
        if compound_matches:
            # 返回第一個匹配的化合物名稱
            return compound_matches[0]
        
        return None
    
    def _extract_sequence(self, basename: str) -> Optional[str]:
        """提取序號（如 01, 02, 001 等）"""
        # 尋找末尾的數字序號
        sequence_match = re.search(r"_(\d{2,3})$", basename)
        if sequence_match:
            return sequence_match.group(1)
        return None
    
    def _extract_instrument_type(self, basename: str) -> Optional[str]:
        """從檔名提取儀器類型"""
        basename_lower = basename.lower()
        
        for instrument_type, patterns in self.KEYWORD_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, basename_lower):
                    return instrument_type
        
        return None
    
    def _generate_tags(
        self,
        file_type: str,
        metadata: Dict[str, Any],
        basename: str
    ) -> List[str]:
        """
        生成建議標籤
        
        Args:
            file_type: 檔案類型
            metadata: 提取的元數據
            basename: 檔案基本名稱
        
        Returns:
            List[str]: 建議的標籤列表
        """
        tags = []
        
        # 1. 添加檔案類型標籤
        if file_type != "Unknown":
            tags.append(file_type)
        
        # 2. 添加樣品相關標籤
        if "sample" in metadata:
            sample = metadata["sample"]
            tags.append(f"sample:{sample}")
            
            # 檢查是否包含元素摻雜
            if re.search(r"Cr\d*", sample, re.IGNORECASE):
                tags.append("Cr-doped")
            if re.search(r"Mn", sample, re.IGNORECASE):
                tags.append("Mn-based")
        
        # 3. 添加日期標籤（年份和月份）
        if "date" in metadata:
            date_str = metadata["date"]
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            tags.append(f"year:{date_obj.year}")
            tags.append(f"month:{date_obj.year}-{date_obj.month:02d}")
        
        # 4. 添加儀器類型標籤
        if "instrument" in metadata:
            instrument = metadata["instrument"]
            if instrument not in tags:
                tags.append(instrument)
        
        # 5. 根據檔名添加其他語義標籤
        basename_lower = basename.lower()
        
        # 結構類型
        if re.search(r"beta", basename_lower):
            tags.append("beta-phase")
        if re.search(r"alpha", basename_lower):
            tags.append("alpha-phase")
        if re.search(r"gamma", basename_lower):
            tags.append("gamma-phase")
        
        # 測試類型
        if re.search(r"cycle", basename_lower):
            tags.append("cycle-test")
        if re.search(r"rate", basename_lower):
            tags.append("rate-test")
        if re.search(r"charge|discharge", basename_lower):
            tags.append("charge-discharge")
        
        # 處理階段
        if re.search(r"raw", basename_lower):
            tags.append("raw-data")
        if re.search(r"processed", basename_lower):
            tags.append("processed")
        if re.search(r"refined", basename_lower):
            tags.append("refined")
        
        return tags
    
    def batch_classify(
        self,
        filenames: List[str],
        contents: Optional[List[Optional[bytes]]] = None
    ) -> List[ClassificationResult]:
        """
        批量分類檔案
        
        Args:
            filenames: 檔案名稱列表
            contents: 檔案內容列表（可選）
        
        Returns:
            List[ClassificationResult]: 分類結果列表
        """
        if contents is None:
            contents = [None] * len(filenames)
        
        results = []
        for filename, content in zip(filenames, contents):
            try:
                result = self.classify_file(filename, content)
                results.append(result)
            except Exception as e:
                self.logger.error(f"分類檔案失敗: {filename}, 錯誤: {str(e)}")
                # 返回一個未知類型的結果
                results.append(
                    ClassificationResult(
                        file_type="Unknown",
                        confidence=0.0,
                        suggested_tags=["unclassified"],
                        metadata={"error": str(e)},
                        source="auto"
                    )
                )
        
        return results
    
    def get_supported_types(self) -> Dict[str, List[str]]:
        """獲取支援的檔案類型和對應的擴展名"""
        return self.FILE_TYPE_EXTENSIONS.copy()
    
    def get_classification_stats(
        self,
        results: List[ClassificationResult]
    ) -> Dict[str, Any]:
        """
        計算分類統計信息
        
        Args:
            results: 分類結果列表
        
        Returns:
            Dict: 統計信息
        """
        if not results:
            return {
                "total": 0,
                "by_type": {},
                "avg_confidence": 0.0,
                "unknown_count": 0
            }
        
        type_counts = {}
        total_confidence = 0.0
        unknown_count = 0
        
        for result in results:
            # 統計類型分佈
            type_counts[result.file_type] = type_counts.get(result.file_type, 0) + 1
            
            # 累計置信度
            total_confidence += result.confidence
            
            # 統計未知類型
            if result.file_type == "Unknown":
                unknown_count += 1
        
        return {
            "total": len(results),
            "by_type": type_counts,
            "avg_confidence": total_confidence / len(results) if results else 0.0,
            "unknown_count": unknown_count,
            "unknown_rate": unknown_count / len(results) if results else 0.0
        }
