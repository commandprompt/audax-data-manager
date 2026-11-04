// Host side of the desktop shell, injected into every page of the main window.
//
// It speaks the same postMessage protocol the old NW.js index.html spoke with the Django
// frontend (utils/clipboard.js, main.js), and bridges the few native features a system
// webview does not provide to the page (external links, file drops, export saves).
(function () {
  if (window.__audaxHostShim) return;
  window.__audaxHostShim = true;

  var invoke = function (cmd, args) {
    return window.__TAURI__.core.invoke(cmd, args);
  };

  // Posts a "pgmanage:<type>" message to the page itself.
  var toPage = function (type, data) {
    window.postMessage(Object.assign({ type: 'pgmanage:' + type }, data), '*');
  };

  var isExternal = function (u) {
    return (u.protocol === 'http:' || u.protocol === 'https:') && u.origin !== window.location.origin;
  };

  // --- messages sent by the page ---------------------------------------------------------
  window.addEventListener('message', function (e) {
    var d = e.data || {};
    switch (d.type) {
      case 'pgmanage:app-ready':
        invoke('app_ready');
        break;
      case 'pgmanage:confirm-close':
        invoke('confirm_close');
        break;
      case 'pgmanage:read-clipboard-text':
        if (!d.requestId) break;
        var reply = function (text) {
          toPage('clipboard-text', { requestId: d.requestId, text: text || '' });
        };
        invoke('read_clipboard').then(reply, function () { reply(''); });
        break;
    }
  });

  // --- links and downloads ---------------------------------------------------------------
  // Query export "Save" links: ask where to save, then copy the server-side export file there.
  // External links and window.open go to the system browser.
  document.addEventListener('click', function (e) {
    var a = e.target && e.target.closest ? e.target.closest('a[href]') : null;
    if (!a) return;
    var u;
    try { u = new URL(a.href, window.location.href); } catch (_) { return; }

    var isExport = a.hasAttribute('download') && u.protocol === 'http:'
      && u.origin === window.location.origin && u.pathname.indexOf('/static/temp/') !== -1;
    if (isExport) {
      e.preventDefault();
      invoke('save_export', { url: u.href, name: a.getAttribute('download') || '' }).catch(
        function (err) { toPage('host-error', { message: 'Could not save the file: ' + err }); }
      );
    } else if (isExternal(u)) {
      e.preventDefault();
      invoke('open_external_url', { url: u.href });
    }
  }, true);

  var nativeOpen = window.open;
  window.open = function (url) {
    try {
      var u = new URL(url, window.location.href);
      if (isExternal(u)) {
        invoke('open_external_url', { url: u.href });
        return null;
      }
    } catch (_) {}
    return nativeOpen.apply(window, arguments);
  };

  // --- file drops ------------------------------------------------------------------------
  // WebKitGTK exposes no File to the page for external drops. The host reports the native drop
  // (real paths) as 'audax-native-drop'; the file is read through the host and a normal drop
  // event is replayed, so the editors' existing drop handlers run unchanged.
  window.addEventListener('audax-native-drop', function (ev) {
    var d = ev.detail || {};
    var paths = d.paths || [];
    if (!paths.length) return;

    var target = document.elementFromPoint(d.x, d.y) || document.body;
    var fire = function (files) {
      var dt = new DataTransfer();
      files.forEach(function (f) { dt.items.add(f); });
      target.dispatchEvent(new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer: dt }));
    };

    if (paths.length > 1) {
      // Names only: the page shows its own "one file at a time" message.
      fire(paths.map(function (p) { return new File([''], p.split(/[\\/]/).pop()); }));
      return;
    }
    invoke('read_dropped_file', { path: paths[0] }).then(
      function (r) { fire([new File([r[1]], r[0])]); },
      function (err) { toPage('host-error', { message: String(err) }); }
    );
  });

  window.addEventListener('load', function () {
    toPage('desktop-host-ready');
  });
})();
