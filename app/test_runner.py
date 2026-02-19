"""
測試集運行器和管理工具

【功能】
- 組織和運行不同類型的測試
- 生成測試報告和覆蓋率統計
- 性能測試支援
- 測試結果分析

【使用】
python -m app.test_runner
python -m app.test_runner --type unit
python -m app.test_runner --type integration
python -m app.test_runner --coverage
"""

import subprocess
import sys
import os
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
import argparse


class TestRunner:
    """測試集運行器"""
    __test__ = False
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.app_dir = self.project_root / "app"
        self.results_dir = self.project_root / "test_results"
        self.results_dir.mkdir(exist_ok=True)
    
    def run_tests(
        self,
        test_type: str = "all",
        coverage: bool = False,
        verbose: bool = True,
        markers: List[str] = None
    ) -> Tuple[int, Dict]:
        """
        運行測試
        
        【參數】
        test_type: all, unit, integration, slow
        coverage: 是否生成覆蓋率報告
        verbose: 詳細輸出
        markers: pytest 標籤
        """
        cmd = [sys.executable, "-m", "pytest"]
        
        # 選擇測試文件
        if test_type == "unit":
            cmd.append(str(self.app_dir / "test_unit.py"))
        elif test_type == "integration":
            cmd.append(str(self.app_dir / "test_integration.py"))
        elif test_type == "all":
            cmd.append(str(self.app_dir))
        else:
            print(f"未知的測試類型: {test_type}")
            return 1, {}
        
        # 添加標籤過濾
        if markers:
            for marker in markers:
                cmd.extend(["-m", marker])
        
        # 添加詳細輸出
        if verbose:
            cmd.append("-v")
        else:
            cmd.append("-q")
        
        # 添加覆蓋率
        if coverage:
            cmd.extend([
                "--cov=app",
                "--cov-report=html:test_results/htmlcov",
                "--cov-report=term-missing",
                "--cov-report=json:test_results/coverage.json"
            ])
        
        # 添加 JUnit 報告
        cmd.extend([
            f"--junit-xml=test_results/junit-{test_type}.xml",
            "-v"
        ])
        
        print(f"運行 {test_type} 測試...")
        print(f"命令: {' '.join(cmd)}\n")
        
        # 記錄開始時間
        start_time = time.time()
        
        # 運行測試
        result = subprocess.run(cmd, cwd=self.project_root)
        
        # 計算耗時
        elapsed = time.time() - start_time
        
        stats = {
            "type": test_type,
            "exit_code": result.returncode,
            "elapsed_seconds": elapsed,
            "timestamp": datetime.now().isoformat()
        }
        
        return result.returncode, stats
    
    def run_all_test_types(self, coverage: bool = True) -> Dict:
        """運行所有類型的測試"""
        print("=" * 70)
        print("LabFlow 測試集運行")
        print("=" * 70)
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {}
        }
        
        total_exit_code = 0
        
        for test_type in ["unit", "integration"]:
            print(f"\n{'=' * 70}")
            print(f"測試集: {test_type.upper()}")
            print(f"{'=' * 70}\n")
            
            exit_code, stats = self.run_tests(
                test_type=test_type,
                coverage=(test_type == "integration" and coverage),
                verbose=True
            )
            
            results["tests"][test_type] = stats
            total_exit_code = max(total_exit_code, exit_code)
        
        # 生成綜合報告
        print(f"\n{'=' * 70}")
        print("測試結果摘要")
        print(f"{'=' * 70}\n")
        
        for test_type, stats in results["tests"].items():
            status = "✅ PASS" if stats["exit_code"] == 0 else "❌ FAIL"
            print(f"{test_type:15} {status:10} ({stats['elapsed_seconds']:.2f}s)")
        
        # 保存結果
        self.save_results(results)
        
        return results
    
    def save_results(self, results: Dict):
        """保存測試結果"""
        result_file = self.results_dir / "summary.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n✅ 測試結果已保存: {result_file}")
    
    def generate_coverage_report(self):
        """生成覆蓋率報告"""
        print("\n生成覆蓋率報告...")
        cmd = [
            sys.executable, "-m", "pytest",
            "--cov=app",
            "--cov-report=html:test_results/htmlcov",
            "--cov-report=term-missing",
            str(self.app_dir)
        ]
        
        result = subprocess.run(cmd, cwd=self.project_root)
        
        if result.returncode == 0:
            print("\n✅ 覆蓋率報告已生成")
            print("打開: test_results/htmlcov/index.html")
        
        return result.returncode
    
    def run_performance_tests(self):
        """運行性能測試（標記為 slow）"""
        print("\n運行性能測試...")
        cmd = [
            sys.executable, "-m", "pytest",
            "-m", "slow",
            "-v",
            str(self.app_dir)
        ]
        
        result = subprocess.run(cmd, cwd=self.project_root)
        return result.returncode


def main():
    """主函數"""
    parser = argparse.ArgumentParser(
        description="LabFlow 測試集運行器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m app.test_runner                      # 運行所有測試
  python -m app.test_runner --type unit          # 只運行單元測試
  python -m app.test_runner --type integration   # 只運行集成測試
  python -m app.test_runner --coverage           # 生成覆蓋率報告
  python -m app.test_runner --performance        # 運行性能測試
        """
    )
    
    parser.add_argument(
        "--type",
        choices=["all", "unit", "integration"],
        default="all",
        help="測試類型 (預設: all)"
    )
    
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="生成覆蓋率報告"
    )
    
    parser.add_argument(
        "--performance",
        action="store_true",
        help="運行性能測試"
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="簡潔輸出"
    )
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    # 運行性能測試
    if args.performance:
        exit_code = runner.run_performance_tests()
        sys.exit(exit_code)
    
    # 運行其他測試
    if args.type == "all":
        results = runner.run_all_test_types(coverage=args.coverage)
        exit_code = max(stats["exit_code"] for stats in results["tests"].values())
    else:
        exit_code, stats = runner.run_tests(
            test_type=args.type,
            coverage=args.coverage,
            verbose=not args.quiet
        )
    
    # 生成覆蓋率報告
    if args.coverage and args.type in ["all", "integration"]:
        runner.generate_coverage_report()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
