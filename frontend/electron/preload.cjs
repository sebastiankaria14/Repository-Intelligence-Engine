const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  isElectron: true,
  // Dialogs & Filesystem
  selectFolder: () => ipcRenderer.invoke('dialog:openDirectory'),

  // App Info & Shell
  getAppInfo: () => ipcRenderer.invoke('app:getInfo'),

  // Window Controls
  minimizeWindow: () => ipcRenderer.send('window:minimize'),
  maximizeWindow: () => ipcRenderer.send('window:maximize'),
  closeWindow: () => ipcRenderer.send('window:close'),

  // Local Analysis Engine IPC Management
  getPipelineStatus: () => ipcRenderer.invoke('pipeline:getStatus'),
  startPipelineEngine: () => ipcRenderer.invoke('pipeline:start'),
  stopPipelineEngine: () => ipcRenderer.invoke('pipeline:stop'),
  restartPipelineEngine: () => ipcRenderer.invoke('pipeline:restart'),
  checkPipelineHealth: () => ipcRenderer.invoke('pipeline:checkHealth'),

  // Stream Listeners
  onPipelineLog: (callback) => {
    const listener = (_event, logData) => callback(logData);
    ipcRenderer.on('pipeline:log', listener);
    return () => ipcRenderer.removeListener('pipeline:log', listener);
  },
  onPipelineStatus: (callback) => {
    const listener = (_event, statusData) => callback(statusData);
    ipcRenderer.on('pipeline:status', listener);
    return () => ipcRenderer.removeListener('pipeline:status', listener);
  },
});
