"""Build the public Kodi repository and GitHub Pages ZIP directory."""
from pathlib import Path
import hashlib
import shutil
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parent
SITE = ROOT / 'docs'
BASE = 'https://fiodger.github.io/kodi-strims24/'
REPO_ID = 'repository.fiodger.strims24'
REPO_VERSION = '1.0.0'
SITE.mkdir(exist_ok=True)
repo_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<addon id="{REPO_ID}" name="Fiodger - Strims24" version="{REPO_VERSION}" provider-name="fiodger">
  <extension point="xbmc.addon.repository" name="Fiodger - Strims24">
    <dir>
      <info>{BASE}addons.xml</info>
      <checksum>{BASE}addons.xml.md5</checksum>
      <datadir>{BASE}</datadir>
      <hashes>false</hashes>
    </dir>
  </extension>
  <extension point="xbmc.addon.metadata">
    <summary lang="pl_PL">Repozytorium dodatku Strims24</summary>
    <description lang="pl_PL">Instalacja i aktualizacje dodatku Strims24 dla Kodi 19+.</description>
    <platform>all</platform><license>MIT</license>
  </extension>
</addon>
'''
repo_dir = SITE / REPO_ID
repo_dir.mkdir(exist_ok=True)
(repo_dir / 'addon.xml').write_text(repo_xml, encoding='utf-8')
repo_zip = repo_dir / f'{REPO_ID}-{REPO_VERSION}.zip'
with zipfile.ZipFile(repo_zip, 'w', zipfile.ZIP_DEFLATED) as archive:
    archive.writestr(f'{REPO_ID}/addon.xml', repo_xml.encode('utf-8'))

addon_xml = ROOT / 'plugin.video.strims24' / 'addon.xml'
addon = ET.parse(addon_xml).getroot()
addon_id, version = addon.attrib['id'], addon.attrib['version']
addon_dir = SITE / addon_id
addon_dir.mkdir(exist_ok=True)
addon_zip = addon_dir / f'{addon_id}-{version}.zip'
with zipfile.ZipFile(addon_zip, 'w', zipfile.ZIP_DEFLATED) as archive:
    for source in sorted(addon_xml.parent.rglob('*')):
        if source.is_file() and '__pycache__' not in source.parts and source.suffix != '.pyc':
            archive.write(source, source.relative_to(ROOT).as_posix())
shutil.copyfile(addon_xml, addon_dir / 'addon.xml')
shutil.copyfile(addon_zip, ROOT / 'dist' / addon_zip.name)
catalog = ET.Element('addons')
catalog.append(addon)
catalog.append(ET.fromstring(repo_xml))
data = ET.tostring(catalog, encoding='utf-8', xml_declaration=True)
(SITE / 'addons.xml').write_bytes(data)
(SITE / 'addons.xml.md5').write_text(hashlib.md5(data).hexdigest(), encoding='ascii')
for package in (repo_zip, addon_zip):
    shutil.copyfile(package, SITE / package.name)
    package.with_suffix('.zip.sha256').write_text(hashlib.sha256(package.read_bytes()).hexdigest(), encoding='ascii')
    with zipfile.ZipFile(package) as archive:
        assert archive.testzip() is None
(SITE / '.nojekyll').write_text('', encoding='ascii')
(SITE / 'index.html').write_text(f'''<!doctype html>
<html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Fiodger - dodatki Kodi</title></head>
<body><h1>Fiodger - dodatki Kodi</h1>
<p>W Kodi dodaj źródło: <strong>{BASE}</strong></p>
<p>Wybierz Dodatki → Zainstaluj z pliku ZIP → to źródło → repository.fiodger.strims24-1.0.0.zip.
Następnie Zainstaluj z repozytorium → Fiodger - Strims24 → Dodatki wideo → Strims24 — transmisje.</p>
<hr><pre><a href="{repo_zip.name}">{repo_zip.name}</a>
<a href="{addon_zip.name}">{addon_zip.name}</a></pre><hr>
<p>Pierwszy ZIP instaluje repozytorium aktualizacji. Drugi pozwala zainstalować sam dodatek.</p>
</body></html>
''', encoding='utf-8')
print(f'Built {BASE}: addon {version}, repository {REPO_VERSION}')
