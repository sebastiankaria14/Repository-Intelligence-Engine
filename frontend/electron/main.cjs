const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const http = require('http');
const { spawn, execFile } = require('child_process');

let mainWindow = null;
let pythonProcess = null;
let isPythonProcessManaged = false;

/**
 * Probe the FastAPI backend /health endpoint
 */
function checkBackendHealth(port = 8000, timeout = 1500) {
  return new Promise((resolve) => {
    const req = http.get(
      {
        hostname: '127.0.0.1',
        port,
        path: '/health',
        timeout,
      },
      (res) => {
        let rawData = '';
        res.on('data', (chunk) => {
          rawData += chunk;
        });
        res.on('end', () => {
          if (res.statusCode === 200) {
            try {
              resolve({ ok: true, data: JSON.parse(rawData) });
            } catch {
              resolve({ ok: true, data: null });
            }
          } else {
            resolve({ ok: false, status: res.statusCode });
          }
        });
      }
    );

    req.on('error', (err) => {
      resolve({ ok: false, error: err.message });
    });

    req.on('timeout', () => {
      req.destroy();
      resolve({ ok: false, error: 'Request timeout' });
    });
  });
}

const fs = require('fs');

/**
 * Resolve the most appropriate Python executable.
 * Prioritizes virtual environments if available, then system Python.
 */
function resolvePythonCommand(rootDir) {
  if (process.env.PYTHON_PATH && fs.existsSync(process.env.PYTHON_PATH)) {
    return process.env.PYTHON_PATH;
  }
  const isWin = process.platform === 'win32';
  const candidates = isWin
    ? [
        path.join(rootDir, '.venv', 'Scripts', 'python.exe'),
        path.join(rootDir, 'venv', 'Scripts', 'python.exe'),
        path.join(rootDir, 'backend', '.venv', 'Scripts', 'python.exe'),
      ]
    : [
        path.join(rootDir, '.venv', 'bin', 'python'),
        path.join(rootDir, 'venv', 'bin', 'python'),
        path.join(rootDir, 'backend', '.venv', 'bin', 'python'),
      ];

  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }

  return isWin ? 'python' : 'python3';
}

/**
 * Start the local Python analysis engine as an Electron child process
 */
async function startPythonBackend() {
  // Check if backend is already running
  const health = await checkBackendHealth();
  if (health.ok) {
    console.log('[Electron] Backend is already running on port 8000');
    broadcastPipelineStatus('running', { managed: false, port: 8000 });
    return { success: true, message: 'Backend already running', managed: false };
  }

  const rootDir = path.join(__dirname, '../../');
  const pythonCmd = resolvePythonCommand(rootDir);
  const args = [
    '-m',
    'uvicorn',
    'app.main:app',
    '--app-dir',
    'backend',
    '--port',
    '8000',
    '--host',
    '127.0.0.1',
  ];

  console.log(`[Electron] Spawning Python engine: ${pythonCmd} ${args.join(' ')} in ${rootDir}`);
  broadcastPipelineStatus('starting', { managed: true, port: 8000 });

  try {
    pythonProcess = spawn(pythonCmd, args, {
      cwd: rootDir,
      env: {
        ...process.env,
        PYTHONUNBUFFERED: '1',
        PYTHONIOENCODING: 'utf-8',
      },
      shell: process.platform === 'win32',
    });

    isPythonProcessManaged = true;

    pythonProcess.stdout.on('data', (data) => {
      const text = data.toString().trim();
      if (text && mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('pipeline:log', { type: 'stdout', message: text, time: Date.now() });
      }
    });

    pythonProcess.stderr.on('data', (data) => {
      const text = data.toString().trim();
      if (text && mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('pipeline:log', { type: 'stderr', message: text, time: Date.now() });
      }
    });

    pythonProcess.on('exit', (code, signal) => {
      console.log(`[Electron] Python engine exited with code: ${code}, signal: ${signal}`);
      pythonProcess = null;
      isPythonProcessManaged = false;
      broadcastPipelineStatus('stopped', { code, signal });
    });

    pythonProcess.on('error', (err) => {
      console.error('[Electron] Failed to start Python engine:', err);
      broadcastPipelineStatus('error', { error: err.message });
    });

    // Wait up to 15 seconds for backend to become healthy
    let attempts = 0;
    while (attempts < 30) {
      await new Promise((r) => setTimeout(r, 500));
      if (!pythonProcess && attempts > 1) {
        return { success: false, message: 'Python backend process exited prematurely' };
      }
      const check = await checkBackendHealth();
      if (check.ok) {
        console.log('[Electron] Python engine is healthy and accepting connections');
        broadcastPipelineStatus('running', { managed: true, pid: pythonProcess?.pid, port: 8000 });
        return { success: true, managed: true, pid: pythonProcess?.pid };
      }
      attempts++;
    }

    return { success: false, message: 'Backend started but health check timed out' };
  } catch (err) {
    console.error('[Electron] Error spawning Python backend:', err);
    broadcastPipelineStatus('error', { error: err.message });
    return { success: false, error: err.message };
  }
}

/**
 * Stop the managed Python backend process cleanly
 */
function stopPythonBackend() {
  return new Promise((resolve) => {
    if (!pythonProcess) {
      resolve({ success: true, message: 'No managed process running' });
      return;
    }

    const pid = pythonProcess.pid;
    console.log(`[Electron] Stopping Python engine (PID: ${pid})`);

    if (process.platform === 'win32' && pid) {
      execFile('taskkill', ['/pid', String(pid), '/T', '/F'], (err) => {
        pythonProcess = null;
        isPythonProcessManaged = false;
        broadcastPipelineStatus('stopped', { pid });
        resolve({ success: true, error: err?.message });
      });
    } else {
      pythonProcess.kill('SIGTERM');
      pythonProcess = null;
      isPythonProcessManaged = false;
      broadcastPipelineStatus('stopped', { pid });
      resolve({ success: true });
    }
  });
}

/**
 * Broadcast pipeline status to renderer
 */
function broadcastPipelineStatus(status, details = {}) {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('pipeline:status', {
      status,
      details,
      timestamp: Date.now(),
    });
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1080,
    minHeight: 700,
    backgroundColor: '#090d16',
    title: 'Repository Intelligence Engine',
    show: false,
    frame: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;
  const devUrl = process.env.ELECTRON_START_URL || 'http://localhost:5173';

  // Security Hardening: Block external navigation inside electron webContents and open safe links in external browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http:') || url.startsWith('https:')) {
      shell.openExternal(url);
    }
    return { action: 'deny' };
  });

  mainWindow.webContents.on('will-navigate', (event, navigationUrl) => {
    // Allow local dev server or index.html file
    if (isDev && navigationUrl.startsWith(devUrl)) {
      return;
    }
    if (!isDev && navigationUrl.startsWith('file://')) {
      return;
    }
    event.preventDefault();
    if (navigationUrl.startsWith('http:') || navigationUrl.startsWith('https:')) {
      shell.openExternal(navigationUrl);
    }
  });

  if (isDev) {
    mainWindow.loadURL(devUrl);
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }

  mainWindow.once('ready-to-show', () => {
    if (mainWindow) {
      mainWindow.show();
      // Probe and announce initial engine status
      void checkBackendHealth().then((health) => {
        broadcastPipelineStatus(health.ok ? 'running' : 'stopped', {
          managed: isPythonProcessManaged,
          port: 8000,
          health: health.data,
        });
      });
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// IPC Handler: Native Directory Selection
ipcMain.handle('dialog:openDirectory', async () => {
  if (!mainWindow) return null;
  const result = await dialog.showOpenDialog(mainWindow, {
    title: 'Select Repository Folder',
    properties: ['openDirectory'],
  });

  if (result.canceled || result.filePaths.length === 0) {
    return null;
  }
  return result.filePaths[0];
});

// IPC Handler: App Information
ipcMain.handle('app:getInfo', async () => {
  return {
    version: app.getVersion(),
    name: app.getName(),
    platform: process.platform,
    userDataPath: app.getPath('userData'),
  };
});

// IPC Handlers: Pipeline Engine Management
ipcMain.handle('pipeline:getStatus', async () => {
  const health = await checkBackendHealth();
  return {
    running: health.ok,
    managed: isPythonProcessManaged,
    pid: pythonProcess?.pid ?? null,
    port: 8000,
    health: health.data ?? null,
  };
});

ipcMain.handle('pipeline:start', async () => {
  return await startPythonBackend();
});

ipcMain.handle('pipeline:stop', async () => {
  return await stopPythonBackend();
});

ipcMain.handle('pipeline:restart', async () => {
  await stopPythonBackend();
  await new Promise((r) => setTimeout(r, 800));
  return await startPythonBackend();
});

ipcMain.handle('pipeline:checkHealth', async () => {
  return await checkBackendHealth();
});

// Window controls
ipcMain.on('window:minimize', () => {
  if (mainWindow) mainWindow.minimize();
});

ipcMain.on('window:maximize', () => {
  if (mainWindow) {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  }
});

ipcMain.on('window:close', () => {
  if (mainWindow) mainWindow.close();
});

// App Lifecycle
app.whenReady().then(async () => {
  createWindow();

  // Always auto-start the local Python analysis engine if not already running
  void startPythonBackend();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('before-quit', async () => {
  if (isPythonProcessManaged && pythonProcess) {
    await stopPythonBackend();
  }
});

app.on('window-all-closed', async () => {
  if (isPythonProcessManaged && pythonProcess) {
    await stopPythonBackend();
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
