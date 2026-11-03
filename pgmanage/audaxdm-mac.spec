# -*- mode: python ; coding: utf-8 -*-
import os

# since pyinstaller does not have option to specify folders to exclude
# we use basic filtering
# https://github.com/orgs/pyinstaller/discussions/6126

exclude_patterns = [
  '.dist-info',
  'django/contrib/humanize',
  'django/contrib/gis',
  'django/contrib/flatpages',
  'django/contrib/sitemaps',
  'django/contrib/syndication',
  'django/contrib/admindocs',
  'django/contrib/admin',
]

block_cipher = None

data_files_server = [
  ('audaxdm.db','.'),
  ('config.py','.'),
  ('app/static/dist','app/static/dist'),
  ('app/static/plugins','app/static/plugins'),
  ('app/static/temp','app/static/temp'),
  ('app/include','app/include'),
  ('app/templates','app/templates'),
  ('app/plugins','app/plugins'),
]


a = Analysis(['pgmanage-server.py'],
             pathex=[],
             binaries=[],
             datas=data_files_server,
             hiddenimports=['cheroot.ssl','cheroot.ssl.builtin','psycopg2','paramiko', 'pkg_resources.extern', 'cryptography.hazmat.primitives.kdf.pbkdf2', 'cryptography.x509'],
             hookspath=[],
             runtime_hooks=[],
             excludes=['django.contrib.gis', 'django.contrib.sitemaps', 'django.contrib.flatpages', 'django.contrib.syndication', 'django.contrib.admindocs', 'django.contrib.humanize', 'django.contrib.admin'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
# config.py gets removed by the next expression, keep it for restoring later
configpy = [entry for entry in a.datas if 'config.py' in entry[0]]
a.datas = [
    entry for entry in a.datas
    if not entry[0].endswith('.py')
    and not entry[0].endswith('.pyc')
    and '__pycache__' not in entry[0]
    and not any(pattern in entry[0] for pattern in exclude_patterns)
]
# strip non-English Django locale catalogs; keep 'en' since Django's gettext machinery
# requires the default language's catalog to exist even though the app never switches languages
a.datas = [entry for entry in a.datas if '/locale/' not in entry[0] or '/locale/en/' in entry[0]]
a.datas = a.datas + configpy

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='audaxdm-server',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True,
          disable_windowed_traceback=False,
          argv_emulation=False,
          target_arch=os.environ.get('PYINSTALLER_TARGET_ARCH'),
          codesign_identity=None,
          entitlements_file=None,
          )

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='audaxdm-server',
)