// file_system.js
// Handles Web File System Access API for LearnOps Phase 1 Extract MVP.

const DB_NAME = 'LearnOps_FS_DB';
const DB_VERSION = 1;
const STORE_NAME = 'handles';
const HANDLE_KEY = 'staging_dir_handle';

function getDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    request.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME);
      }
    };
  });
}

async function setHandle(handle) {
  const db = await getDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    const request = store.put(handle, HANDLE_KEY);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

async function getHandle() {
  try {
    const db = await getDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly');
      const store = tx.objectStore(STORE_NAME);
      const request = store.get(HANDLE_KEY);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  } catch (err) {
    return null; // DB might not exist or failed
  }
}

async function verifyPermission(handle, mode = 'readwrite') {
  const options = { mode };
  if ((await handle.queryPermission(options)) === 'granted') {
    return true;
  }
  if ((await handle.requestPermission(options)) === 'granted') {
    return true;
  }
  return false;
}

const FileSystem = {
  async initDirectoryPicker() {
    try {
      const handle = await window.showDirectoryPicker({ mode: 'readwrite' });
      await setHandle(handle);
      return true;
    } catch (err) {
      console.warn('Directory picker cancelled or failed:', err);
      return false;
    }
  },

  async hasDirectorySelected() {
    const handle = await getHandle();
    return !!handle;
  },

  async getDirectoryName() {
    const handle = await getHandle();
    return handle ? handle.name : null;
  },

  async writeStagingFile(filename, content) {
    let handle = await getHandle();
    if (!handle) {
      throw new Error('No Staging directory selected. Please configure it in Settings.');
    }
    const hasPerms = await verifyPermission(handle, 'readwrite');
    if (!hasPerms) {
      throw new Error('Permission denied to write to the Staging directory.');
    }

    try {
      const fileHandle = await handle.getFileHandle(filename, { create: true });
      const writable = await fileHandle.createWritable();
      await writable.write(content);
      await writable.close();
      return true;
    } catch (err) {
      console.error('FS Write Error:', err);
      throw new Error('Failed to save file: ' + err.message);
    }
  }
};

window.FileSystem = FileSystem;
