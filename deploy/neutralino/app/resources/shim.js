// Host side of the Neutralino shell, injected into every page of every window.
//
// On the application page it speaks the same postMessage protocol the Django frontend uses with
// the other desktop shells (utils/clipboard.js, main.js) and provides the few native features a
// system webview does not: external links, file drops, file dialogs and saves.
(function () {
  if (window.__audaxHostShim) return;
  window.__audaxHostShim = true;

  // Only the main window (started by the launcher with --url) runs this; the splash page is the
  // launcher itself and has its own script.
  if (!(window.NL_ARGS || []).some(function (a) { return a.indexOf('--url=') === 0; })) return;

  var N = function () { return window.Neutralino; };
  var MAX_SAVED_BYTES = 200 * 1024 * 1024;
  var PART_SUFFIX = '.audaxdm-part';
  var REVEAL_FALLBACK_MS = 30000;

  var toPage = function (type, data) {
    window.postMessage(Object.assign({ type: 'pgmanage:' + type }, data), '*');
  };
  var hostError = function (message) { toPage('host-error', { message: String(message) }); };

  // --- window reveal, geometry and close ---------------------------------------------------------
  // The launcher starts this window hidden and keeps its splash up. Once the page reports it is
  // mounted (or a fallback delay passes, so a broken page is still visible) the window is placed
  // at its saved geometry and shown, and the launcher (which reads this process's standard output)
  // is told to hide the splash.
  var MIN_W = 1024, MIN_H = 768;
  var revealed = false;

  function loadState() {
    return N().storage.getData('windowState').then(function (d) { return JSON.parse(d); }, function () { return {}; });
  }
  // Maximized windows keep the previously saved normal size and position.
  function saveState() {
    return Promise.all([loadState(), N().window.isMaximized()]).then(function (r) {
      var state = r[0], maximized = r[1];
      if (maximized) { state.maximized = true; return state; }
      return Promise.all([N().window.getSize(), N().window.getPosition()]).then(function (g) {
        return { width: g[0].width, height: g[0].height, x: g[1].x, y: g[1].y, maximized: false };
      });
    }).then(function (state) {
      return N().storage.setData('windowState', JSON.stringify(state));
    }).catch(function () {});
  }

  // The saved position is only reused if it lies inside the primary display.
  function positionIsUsable(st, w, h) {
    if (!Number.isFinite(st.x) || !Number.isFinite(st.y)) return Promise.resolve(false);
    return N().computer.getDisplays().then(function (displays) {
      var d = displays[0];
      return !!d && st.x >= 0 && st.y >= 0 && st.x + 100 < d.resolution.width && st.y + 100 < d.resolution.height;
    }, function () { return false; });
  }

  function reveal() {
    if (revealed) return;
    revealed = true;
    loadState().then(function (st) {
      var w = Math.max(MIN_W, Number(st.width) || MIN_W), h = Math.max(MIN_H, Number(st.height) || MIN_H);
      return positionIsUsable(st, w, h).then(function (usable) {
        return N().window.setSize({ width: w, height: h, minWidth: MIN_W, minHeight: MIN_H, resizable: true })
          .then(function () { return N().window.show(); })
          // The window manager ignores the position of a hidden window, so it is set once shown.
          .then(function () { return usable ? N().window.move(st.x, st.y) : N().window.center(); })
          .then(function () { return st.maximized ? N().window.maximize() : null; })
          .then(function () { return N().window.focus(); });
      });
    }).catch(function (e) {
      hostError('Could not restore the window: ' + (e && e.message || e));
      return N().window.show();
    }).then(function () { return N().app.writeProcessOutput('mainReady\n'); });
  }

  // --- file dialogs ----------------------------------------------------------------------------
  // The destination of every save is chosen by the user in a native dialog, never by the page.
  var dirOf = function (path) { return path.replace(/[\\/][^\\/]*$/, '') || path; };

  function lastDir() {
    return N().storage.getData('lastDir').then(function (d) { return d || null; }, function () { return null; });
  }
  function rememberDir(path, isFolder) {
    return N().storage.setData('lastDir', isFolder ? path : dirOf(path)).catch(function () {});
  }
  function sanitizeFileName(name) {
    var n = (name || '').split(/[\\/]/).pop().replace(/[\u0000-\u001f]/g, '').trim();
    return n && n !== '.' && n !== '..' ? n : 'file';
  }
  function askSavePath(title, suggested) {
    return lastDir().then(function (dir) {
      return N().os.showSaveDialog(title, { defaultPath: dir ? dir + '/' + suggested : suggested });
    });
  }

  function pickPath(kind, title) {
    return lastDir().then(function (dir) {
      var opts = dir ? { defaultPath: dir } : {};
      var t = title || '';
      if (kind === 'select_folder') {
        return N().os.showFolderDialog(t, opts).then(function (p) { return p ? (rememberDir(p, true), p) : null; });
      }
      if (kind === 'create_file') {
        return N().os.showSaveDialog(t, opts).then(function (p) { return p ? (rememberDir(p), p) : null; });
      }
      return N().os.showOpenDialog(t, opts).then(function (r) { var p = r && r[0]; return p ? (rememberDir(p), p) : null; });
    });
  }

  // --- saving files ----------------------------------------------------------------------------
  // Files are written through a sibling ".audaxdm-part" file and renamed into place only after
  // the write succeeded, so a failed save never damages an existing file.
  function finishPart(part, dest) {
    return N().filesystem.move(part, dest);
  }
  function discardPart(part) {
    return N().filesystem.remove(part).catch(function () {});
  }

  function saveFile(bytes, encodedName) {
    var name = sanitizeFileName(decodeURIComponent(encodedName || ''));
    if (bytes.length > MAX_SAVED_BYTES) return Promise.reject('file is too large to save');
    return askSavePath('Save file', name).then(function (dest) {
      if (!dest) return null;
      var part = dest + PART_SUFFIX;
      return N().filesystem.writeBinaryFile(part, bytes)
        .then(function () { return finishPart(part, dest); })
        .then(function () { rememberDir(dest); return dest; })
        .catch(function (e) { return discardPart(part).then(function () { throw e; }); });
    });
  }

  // Save link of a query export: ask where to save, then copy the server-side export file there.
  function saveExport(url, suggestedName) {
    var name = sanitizeFileName(suggestedName || decodeURIComponent(url.pathname.split('/').pop()));
    return askSavePath('Save file', name).then(function (dest) {
      if (!dest) return;
      var part = dest + PART_SUFFIX, total = 0, first = true;
      return fetch(url.href).then(function (resp) {
        if (!resp.ok) throw new Error('server answered ' + resp.status);
        var reader = resp.body.getReader();
        var pump = function () {
          return reader.read().then(function (r) {
            if (r.done) return;
            total += r.value.length;
            if (total > MAX_SAVED_BYTES) throw new Error('file is too large to save');
            var write = first ? N().filesystem.writeBinaryFile(part, r.value) : N().filesystem.appendBinaryFile(part, r.value);
            first = false;
            return write.then(pump);
          });
        };
        return pump();
      }).then(function () { return first ? N().filesystem.writeBinaryFile(part, new Uint8Array(0)) : null; })
        .then(function () { return finishPart(part, dest); })
        .then(function () { rememberDir(dest); })
        .catch(function (e) { return discardPart(part).then(function () { throw e; }); });
    });
  }

  // The frontend (utils/native_dialog.js) talks to its desktop shell through this invoke shape.
  window.__TAURI__ = {
    core: {
      invoke: function (cmd, args, options) {
        if (cmd === 'pick_path') return pickPath(args.kind, args.title);
        if (cmd === 'save_file') return saveFile(args, options && options.headers && options.headers['x-file-name']);
        return Promise.reject('unknown command: ' + cmd);
      }
    }
  };

  // --- messages sent by the page ---------------------------------------------------------------
  window.addEventListener('message', function (e) {
    var d = e.data || {};
    switch (d.type) {
      case 'pgmanage:app-ready':
        reveal();
        break;
      case 'pgmanage:confirm-close':
        saveState().then(function () { N().app.exit(); });
        break;
      case 'pgmanage:read-clipboard-text':
        if (!d.requestId) break;
        N().clipboard.readText().then(
          function (text) { toPage('clipboard-text', { requestId: d.requestId, text: text || '' }); },
          function () { toPage('clipboard-text', { requestId: d.requestId, text: '' }); }
        );
        break;
    }
  });

  // --- links and downloads ---------------------------------------------------------------------
  var isExternal = function (u) {
    return (u.protocol === 'http:' || u.protocol === 'https:') && u.origin !== window.location.origin;
  };
  document.addEventListener('click', function (e) {
    var a = e.target && e.target.closest ? e.target.closest('a[href]') : null;
    if (!a) return;
    var u;
    try { u = new URL(a.href, window.location.href); } catch (_) { return; }
    var isExport = a.hasAttribute('download') && u.protocol === 'http:'
      && u.origin === window.location.origin && u.pathname.indexOf('/static/temp/') !== -1;
    if (isExport) {
      e.preventDefault();
      saveExport(u, a.getAttribute('download') || '').catch(function (err) { hostError('Could not save the file: ' + err); });
    } else if (isExternal(u)) {
      e.preventDefault();
      N().os.open(u.href);
    }
  }, true);

  var nativeOpen = window.open;
  window.open = function (url) {
    try {
      var u = new URL(url, window.location.href);
      if (isExternal(u)) { N().os.open(u.href); return null; }
    } catch (_) {}
    return nativeOpen.apply(window, arguments);
  };

  // --- file drops ------------------------------------------------------------------------------
  // WebKitGTK exposes no File to the page for external drops. The framework reports the native
  // drop (real paths); the file is read here and a normal drop event is replayed, so the editors'
  // existing drop handlers run unchanged. The drop lands where the pointer last was.
  var lastX = 0, lastY = 0;
  document.addEventListener('mousemove', function (e) { lastX = e.clientX; lastY = e.clientY; }, true);

  function onDrop(ev) {
    var paths = ev.detail || [];
    if (!paths.length) return;
    var target = document.elementFromPoint(lastX, lastY) || document.body;
    var fire = function (files) {
      var dt = new DataTransfer();
      files.forEach(function (f) { dt.items.add(f); });
      target.dispatchEvent(new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer: dt }));
    };
    var nameOf = function (p) { return p.split(/[\\/]/).pop(); };
    if (paths.length > 1) {
      // Names only: the page shows its own "one file at a time" message.
      fire(paths.map(function (p) { return new File([''], nameOf(p)); }));
      return;
    }
    N().filesystem.readBinaryFile(paths[0]).then(
      function (buf) { fire([new File([buf], nameOf(paths[0]))]); },
      function (err) { hostError('Could not read the dropped file: ' + (err && err.message || err)); }
    );
  }

  // --- start-up --------------------------------------------------------------------------------
  var tries = 0;
  var wait = setInterval(function () {
    if (!N()) { if (++tries > 200) clearInterval(wait); return; }
    clearInterval(wait);
    N().init();
    N().events.on('filesDropped', onDrop);
    N().events.on('windowClose', function () {
      if (revealed) toPage('request-close'); else N().app.exit();
    });
    var onLoaded = function () {
      toPage('desktop-host-ready');
      setTimeout(reveal, REVEAL_FALLBACK_MS);
    };
    if (document.readyState === 'complete') onLoaded(); else window.addEventListener('load', onLoaded);
  }, 20);
})();
