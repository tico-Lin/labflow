import os
import hashlib
import json
import re
import uuid
from typing import Any, Dict, Optional
from fastapi import UploadFile


class LocalStorage:
    """
    本機硬碟儲存實作
    
    將上傳檔案儲存到本機指定目錄
    
    Attributes:
        base_dir: 儲存根目錄（預設從環境變數 STORAGE_PATH 讀取）
    
    環境變數：
        STORAGE_PATH: 自訂儲存路徑（未設定時預設為 data/managed）
    """
    
    def __init__(self, base_dir: str | None = None):
        """
        初始化本機儲存
        
        Args:
            base_dir: 自訂儲存目錄（優先權高於環境變數）
        """
        # 從環境變數取得儲存路徑，若未設定就預設到 data/managed
        self.base_dir = base_dir or os.getenv("STORAGE_PATH", "data/managed")
        # 確保目錄存在（不存在則自動建立）
        os.makedirs(self.base_dir, exist_ok=True)

    async def save(self, file_or_hash, file_obj=None):
        """
        儲存檔案
        
        支援兩種調用方式:
        1. save(file_obj) - 單一參數方式
        2. save(file_hash, file_obj) - 雙參數方式
        Returns:
            str: 完整檔案路徑
        """
        # 檢測調用模式
        if file_obj is None:
            # 單一參數模式: save(file_obj)
            file_obj = file_or_hash
            file_hash = await calculate_file_hash(file_obj)
        else:
            # 雙參數模式: save(file_hash, file_obj)
            file_hash = file_or_hash
        # 儲存檔案
        filename = f"{file_hash}.bin"
        file_path = os.path.join(self.base_dir, filename)

        # 確保檔案指針在開頭
        await file_obj.seek(0)
        with open(file_path, "wb") as f:
            f.write(await file_obj.read())
        return file_path

    # 兼容性方法
    async def save_with_hash(self, file_obj, file_hash):
        """使用 hash 儲存檔案 (兼容性方法)"""
        return await self.save(file_hash, file_obj)

    def load(self, key: str) -> bytes:
        """
        讀取本機檔案
        
        Args:
            key: 檔案完整路徑
            
        Returns:
            bytes: 檔案內容
        """
        if not os.path.exists(key):
            raise FileNotFoundError(f"File not found at {key}")
        with open(key, "rb") as f:
            return f.read()
    def delete(self, key: str):
        """
        刪除本機檔案
        
        Args:
            key: 檔案完整路徑
        """
        if os.path.exists(key):
            os.remove(key)


class Hdf5Storage:
    """
    HDF5 storage for curve/array data.

    Environment:
        HDF5_PATH: base directory for HDF5 files (default: data/managed/hdf5)
    """

    def __init__(self, base_dir: str | None = None):
        self.base_dir = base_dir or os.getenv("HDF5_PATH", "data/managed/hdf5")
        os.makedirs(self.base_dir, exist_ok=True)

    def save_arrays(
        self,
        name: str,
        arrays: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        try:
            import h5py
        except ImportError as exc:
            raise RuntimeError("h5py not available") from exc

        safe_name = self._safe_stem(name)
        filename = f"{safe_name}_{uuid.uuid4().hex}.h5"
        path = os.path.join(self.base_dir, filename)

        with h5py.File(path, "w") as handle:
            if metadata:
                for key, value in metadata.items():
                    handle.attrs[key] = self._encode_attr(value)
            for key, value in arrays.items():
                handle.create_dataset(key, data=value)

        return path

    def _safe_stem(self, name: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", name or "dataset")
        return cleaned.strip("_") or "dataset"

    def _encode_attr(self, value: Any) -> Any:
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(value, ensure_ascii=True)
        return value

# --- 工具函式：計算檔案 Hash (指紋) ---
async def calculate_file_hash(file: UploadFile) -> str:
    """
    計算檔案的 SHA-256 雜湊值（檔案指紋）
    
    用途：
    - 檢查檔案是否重複（相同內容會產生相同 hash）
    - 可作為唯一檔名使用
    - 驗證檔案完整性
    
    Args:
        file: FastAPI 上傳檔案物件
        
    Returns:
        str: 64 字元的十六進位 SHA-256 雜湊值
        
    Note:
        函式會自動將檔案讀取指針重置到開頭，不影響後續讀取
    """
    sha256_hash = hashlib.sha256()
    
    # 分塊讀取檔案內容計算 hash（避免大檔案記憶體溢位）
    while chunk := await file.read(4096):
        sha256_hash.update(chunk)
    
    # 計算完後，必須把讀取指針歸零，不然之後存檔會讀不到內容
    await file.seek(0)
    
    return sha256_hash.hexdigest()
