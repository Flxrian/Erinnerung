# Baut den Programmordner build\app für den Installer:
#   build\app\python  – offizielles, von der Python Software Foundation signiertes Python
#   build\app\jarvis  – Jarvis selbst (nur .py-Dateien, keine eigene .exe)
#
# Hintergrund: Windows 11 "Smart App Control" blockiert unsignierte Programme
# wie eine selbst gebaute Jarvis.exe (Fehler 4551). Gestartet wird Jarvis
# daher über das signierte pythonw.exe.
#
# Aufruf (mit installiertem Python derselben Version):  .\build_windows.ps1

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$out = Join-Path $root "build\app"
$pyDir = Join-Path $out "python"
$appDir = Join-Path $out "jarvis"

$version = (python -c "import platform; print(platform.python_version())").Trim()
Write-Host "Python-Version: $version"

if (Test-Path $out) { Remove-Item $out -Recurse -Force }
New-Item -ItemType Directory -Force $pyDir, $appDir | Out-Null

# 1. Offizielles Python (embeddable package von python.org)
$zip = Join-Path $root "build\python-$version-embed-amd64.zip"
if (-not (Test-Path $zip)) {
    Invoke-WebRequest "https://www.python.org/ftp/python/$version/python-$version-embed-amd64.zip" -OutFile $zip
}
Expand-Archive $zip -DestinationPath $pyDir -Force

foreach ($exe in "python.exe", "pythonw.exe") {
    $sig = Get-AuthenticodeSignature (Join-Path $pyDir $exe)
    if ($sig.Status -ne "Valid") { throw "$exe ist nicht gültig signiert: $($sig.Status)" }
    Write-Host "$exe signiert von: $($sig.SignerCertificate.Subject)"
}

# Suchpfad: Pakete und Jarvis-Code, site-Modul aktivieren
$pth = Get-ChildItem $pyDir -Filter "python*._pth" | Select-Object -First 1
$zipName = $pth.BaseName + ".zip"
Set-Content -Path $pth.FullName -Encoding ascii -Value @($zipName, ".", "Lib\site-packages", "..\jarvis", "import site")

# 2. Pakete (fertige Wheels bevorzugt; reine Python-Pakete wie pyautogui gibt es nur als Quellpaket)
python -m pip install --disable-pip-version-check --no-warn-script-location --prefer-binary `
    --target (Join-Path $pyDir "Lib\site-packages") -r (Join-Path $root "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "pip install fehlgeschlagen" }

# Mitgelieferte .exe-Hilfsprogramme von Paketen werden nicht gebraucht und wären
# unsigniert – entfernen (z.B. flac-win32.exe; die Spracherkennung schickt PCM).
Get-ChildItem (Join-Path $pyDir "Lib\site-packages") -Recurse -Filter *.exe | ForEach-Object {
    Write-Host "Entferne $($_.FullName)"
    Remove-Item $_.FullName -Force
}

# 3. Jarvis
Get-ChildItem $root -Filter *.py | Copy-Item -Destination $appDir
Copy-Item (Join-Path $root "static") -Destination $appDir -Recurse
Copy-Item (Join-Path $root "assets") -Destination $appDir -Recurse

# 4. Selbsttest mit genau diesem Python
$env:JARVIS_DATA_DIR = Join-Path $root "build\selftest-data"
& (Join-Path $pyDir "python.exe") (Join-Path $appDir "jarvis_app.py") --selftest
if ($LASTEXITCODE -ne 0) { throw "Selbsttest fehlgeschlagen" }
Remove-Item Env:JARVIS_DATA_DIR

# Übersicht: alle ausführbaren Dateien und ihre Signatur
Get-ChildItem $out -Recurse -Include *.exe | ForEach-Object {
    "{0,-12} {1}" -f (Get-AuthenticodeSignature $_.FullName).Status, $_.FullName.Substring($out.Length)
}
Write-Host "Fertig: $out"
