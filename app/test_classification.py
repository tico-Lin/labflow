"""
檔案自動分類服務測試

測試檔案分類功能的各種情況：
- 不同檔案類型（XRD, SEM, EIS等）
- 不同命名規範
- 元數據提取
- 標籤建議
"""

import pytest
from app.services.classification_service import FileClassificationService, ClassificationResult


class TestFileClassificationService:
    """檔案分類服務測試"""
    
    @pytest.fixture
    def service(self):
        """創建分類服務實例"""
        return FileClassificationService()
    
    def test_classify_xrd_file(self, service):
        """測試XRD檔案分類"""
        # 測試標準XRD命名格式
        result = service.classify_file("Cr3_XRD_20250104.xy")
        
        assert result.file_type == "XRD"
        assert result.confidence > 0.8
        assert "XRD" in result.suggested_tags
        assert "sample" in result.metadata
        assert result.metadata["sample"] == "Cr3"
        assert "date" in result.metadata
        assert result.metadata["date"] == "2025-01-04"
    
    def test_classify_sem_file(self, service):
        """測試SEM檔案分類"""
        result = service.classify_file("Sample_A_SEM_2025-01-15_01.tif")
        
        assert result.file_type == "SEM"
        assert result.confidence > 0.8
        assert "SEM" in result.suggested_tags
        assert "sample" in result.metadata
        assert result.metadata["date"] == "2025-01-15"
        assert result.metadata.get("sequence") == "01"
    
    def test_classify_eis_file(self, service):
        """測試EIS檔案分類"""
        result = service.classify_file("EIS_MnO2_20250110.txt")
        
        assert result.file_type == "EIS"
        assert result.confidence > 0.8
        assert "EIS" in result.suggested_tags
        assert "sample" in result.metadata
        assert result.metadata["sample"] == "MnO2"
    
    def test_classify_with_phase_info(self, service):
        """測試包含相位信息的檔名"""
        result = service.classify_file("MnO2-Cr3-beta_XRD.xy")
        
        assert result.file_type == "XRD"
        assert "beta-phase" in result.suggested_tags
        assert "XRD" in result.suggested_tags
    
    def test_classify_cycle_test(self, service):
        """測試循環測試檔案"""
        result = service.classify_file("Battery_cycle_test_20250115.csv")
        
        assert "cycle-test" in result.suggested_tags
        assert "date" in result.metadata
    
    def test_classify_unknown_file(self, service):
        """測試未知類型檔案"""
        result = service.classify_file("random_file.xyz")
        
        assert result.file_type == "Unknown"
        assert result.confidence < 0.5
    
    def test_extract_compound_name(self, service):
        """測試化合物名稱提取"""
        # 測試簡單化合物
        result = service.classify_file("LiFePO4_XRD.xy")
        assert "sample" in result.metadata
        
        # 測試有摻雜的樣品
        result = service.classify_file("Cr3_doped_MnO2.xy")
        assert "Cr-doped" in result.suggested_tags
    
    def test_extract_temperature(self, service):
        """測試溫度信息提取"""
        result = service.classify_file("Sample_A_300C_XRD.xy")
        
        assert "temperature" in result.metadata
        assert "300°C" in result.metadata["temperature"]
    
    def test_batch_classification(self, service):
        """測試批量分類"""
        filenames = [
            "Cr3_XRD_20250104.xy",
            "Sample_A_SEM_01.tif",
            "EIS_MnO2.txt",
            "unknown.xyz"
        ]
        
        results = service.batch_classify(filenames)
        
        assert len(results) == 4
        assert results[0].file_type == "XRD"
        assert results[1].file_type == "SEM"
        assert results[2].file_type == "EIS"
        assert results[3].file_type == "Unknown"
    
    def test_classification_stats(self, service):
        """測試分類統計"""
        filenames = [
            "file1_XRD.xy",
            "file2_XRD.xy",
            "file3_SEM.tif",
            "unknown.xyz"
        ]
        
        results = service.batch_classify(filenames)
        stats = service.get_classification_stats(results)
        
        assert stats["total"] == 4
        assert stats["by_type"]["XRD"] == 2
        assert stats["by_type"]["SEM"] == 1
        assert stats["unknown_count"] == 1
        assert stats["unknown_rate"] == 0.25
    
    def test_supported_types(self, service):
        """測試獲取支援的檔案類型"""
        supported = service.get_supported_types()
        
        assert "XRD" in supported
        assert "SEM" in supported
        assert "EIS" in supported
        assert ".xy" in supported["XRD"]
        assert ".tif" in supported["SEM"]
    
    def test_date_formats(self, service):
        """測試不同日期格式的識別"""
        # YYYYMMDD
        result = service.classify_file("Sample_20250104.xy")
        assert "date" in result.metadata
        assert result.metadata["date"] == "2025-01-04"
        
        # YYYY-MM-DD
        result = service.classify_file("Sample_2025-01-04.xy")
        assert "date" in result.metadata
        assert result.metadata["date"] == "2025-01-04"
        
        # YYYY_MM_DD
        result = service.classify_file("Sample_2025_01_04.xy")
        assert "date" in result.metadata
        assert result.metadata["date"] == "2025-01-04"
    
    def test_classification_confidence(self, service):
        """測試分類置信度"""
        # 高置信度：檔名和擴展名都匹配
        result = service.classify_file("XRD_sample.xy")
        assert result.confidence > 0.9
        
        # 中等置信度：只有擴展名匹配
        result = service.classify_file("sample.xy")
        assert 0.7 < result.confidence < 0.9
        
        # 低置信度：未知類型
        result = service.classify_file("sample.xyz")
        assert result.confidence < 0.5
    
    def test_tag_generation_logic(self, service):
        """測試標籤生成邏輯"""
        result = service.classify_file("Cr3-MnO2_beta_XRD_2025-01-04.xy")
        
        # 應該包含檔案類型標籤
        assert "XRD" in result.suggested_tags
        
        # 應該包含相位標籤
        assert "beta-phase" in result.suggested_tags
        
        # 應該包含年份標籤
        assert any(tag.startswith("year:") for tag in result.suggested_tags)
        
        # 應該包含月份標籤
        assert any(tag.startswith("month:") for tag in result.suggested_tags)
        
        # 應該包含摻雜標籤
        assert "Cr-doped" in result.suggested_tags or "Mn-based" in result.suggested_tags


if __name__ == "__main__":
    # 簡單的手動測試
    service = FileClassificationService()
    
    test_files = [
        "Cr3_XRD_20250104.xy",
        "Sample_A_SEM_2025-01-15_01.tif",
        "EIS_MnO2_20250110.txt",
        "Battery_cycle_test.csv",
        "MnO2-beta-phase.xy",
        "unknown_file.xyz",
    ]
    
    print("檔案自動分類測試")
    print("=" * 80)
    
    for filename in test_files:
        result = service.classify_file(filename)
        print(f"\n檔案: {filename}")
        print(f"  類型: {result.file_type}")
        print(f"  置信度: {result.confidence:.2f}")
        print(f"  建議標籤: {', '.join(result.suggested_tags)}")
        print(f"  元數據: {result.metadata}")
    
    print("\n" + "=" * 80)
    print("批量分類統計")
    print("=" * 80)
    
    results = service.batch_classify(test_files)
    stats = service.get_classification_stats(results)
    
    print(f"\n總共分類: {stats['total']} 個檔案")
    print(f"平均置信度: {stats['avg_confidence']:.2f}")
    print(f"未知檔案數: {stats['unknown_count']} ({stats['unknown_rate']:.1%})")
    print(f"\n類型分佈:")
    for file_type, count in stats['by_type'].items():
        print(f"  {file_type}: {count}")
