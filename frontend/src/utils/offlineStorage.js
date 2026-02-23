/**
 * 離線模式文件存儲管理
 * 使用 IndexedDB 和 localStorage 存儲本地文件
 */

const DB_NAME = 'LabFlow-OfflineDB';
const DB_VERSION = 1;
const STORE_NAME = 'files';

class OfflineStorageManager {
  constructor() {
    this.db = null;
    this.initialized = false;
  }

  /**
   * 初始化 IndexedDB
   */
  async init() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onerror = () => reject(new Error('Failed to open IndexedDB'));
      request.onsuccess = () => {
        this.db = request.result;
        this.initialized = true;
        resolve(this.db);
      };

      request.onupgradeneeded = event => {
        const db = event.target.result;
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          db.createObjectStore(STORE_NAME, { keyPath: 'id' });
        }
      };
    });
  }

  /**
   * 檢查是否已初始化
   */
  async ensureInitialized() {
    if (!this.initialized) {
      await this.init();
    }
  }

  /**
   * 存儲文件
   */
  async storeFile(file) {
    await this.ensureInitialized();

    return new Promise((resolve, reject) => {
      const reader = new FileReader();

      reader.onload = async e => {
        try {
          const fileData = {
            id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
            filename: file.name,
            size: file.size,
            type: file.type,
            content: e.target.result,
            uploadedAt: new Date().toISOString(),
            isLocal: true,
          };

          const transaction = this.db.transaction([STORE_NAME], 'readwrite');
          const store = transaction.objectStore(STORE_NAME);
          const request = store.add(fileData);

          request.onsuccess = () => {
            resolve(fileData);
          };

          request.onerror = () => {
            reject(new Error('Failed to store file'));
          };
        } catch (error) {
          reject(error);
        }
      };

      reader.onerror = () => {
        reject(new Error('Failed to read file'));
      };

      reader.readAsArrayBuffer(file);
    });
  }

  /**
   * 獲取所有本地文件
   */
  async getAllFiles() {
    await this.ensureInitialized();

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([STORE_NAME], 'readonly');
      const store = transaction.objectStore(STORE_NAME);
      const request = store.getAll();

      request.onsuccess = () => {
        // 轉換 ArrayBuffer 為 Blob，便於後續使用
        const files = request.result.map(file => ({
          ...file,
          blob: new Blob([file.content], { type: file.type }),
          isLocal: true,
        }));
        resolve(files);
      };

      request.onerror = () => {
        reject(new Error('Failed to retrieve files'));
      };
    });
  }

  /**
   * 根據 ID 獲取文件
   */
  async getFile(id) {
    await this.ensureInitialized();

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([STORE_NAME], 'readonly');
      const store = transaction.objectStore(STORE_NAME);
      const request = store.get(id);

      request.onsuccess = () => {
        const file = request.result;
        if (file) {
          file.blob = new Blob([file.content], { type: file.type });
          file.isLocal = true;
          resolve(file);
        } else {
          reject(new Error('File not found'));
        }
      };

      request.onerror = () => {
        reject(new Error('Failed to retrieve file'));
      };
    });
  }

  /**
   * 刪除文件
   */
  async deleteFile(id) {
    await this.ensureInitialized();

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([STORE_NAME], 'readwrite');
      const store = transaction.objectStore(STORE_NAME);
      const request = store.delete(id);

      request.onsuccess = () => {
        resolve();
      };

      request.onerror = () => {
        reject(new Error('Failed to delete file'));
      };
    });
  }

  /**
   * 清空所有文件
   */
  async clearAllFiles() {
    await this.ensureInitialized();

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([STORE_NAME], 'readwrite');
      const store = transaction.objectStore(STORE_NAME);
      const request = store.clear();

      request.onsuccess = () => {
        resolve();
      };

      request.onerror = () => {
        reject(new Error('Failed to clear files'));
      };
    });
  }

  /**
   * 獲取存儲大小統計
   */
  async getStorageStats() {
    await this.ensureInitialized();

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([STORE_NAME], 'readonly');
      const store = transaction.objectStore(STORE_NAME);
      const request = store.getAll();

      request.onsuccess = () => {
        const files = request.result;
        const totalSize = files.reduce((sum, file) => sum + file.size, 0);
        const count = files.length;

        resolve({
          fileCount: count,
          totalSize,
          totalSizeMB: (totalSize / (1024 * 1024)).toFixed(2),
        });
      };

      request.onerror = () => {
        reject(new Error('Failed to get storage stats'));
      };
    });
  }
}

// 創建單一實例
export const offlineStorage = new OfflineStorageManager();
