; Inno-Setup-Skript für Jarvis-Setup.exe
; Vorher build_windows.ps1 ausführen, dann:  ISCC.exe /DAppVersion=3.0.1 installer.iss
;
; Jarvis wird über das mitgelieferte, signierte pythonw.exe gestartet – eine
; eigene unsignierte Jarvis.exe würde von Windows' Smart App Control
; blockiert (Fehler 4551).

#ifndef AppVersion
  #define AppVersion "3.0.1"
#endif

#define Launcher "{app}\python\pythonw.exe"
#define Script "{app}\jarvis\jarvis_app.py"

[Setup]
AppId={{8C1E3F4A-6B2D-4E59-9A7B-3D1F0C2E5A91}
AppName=Jarvis
AppVersion={#AppVersion}
AppVerName=Jarvis {#AppVersion}
AppPublisher=Jarvis
DefaultDirName={localappdata}\Programs\Jarvis
DefaultGroupName=Jarvis
DisableProgramGroupPage=yes
; Installation nur für den eigenen Benutzer – keine Adminrechte nötig
PrivilegesRequired=lowest
OutputDir=dist-installer
OutputBaseFilename=Jarvis-Setup
SetupIconFile=assets\jarvis.ico
UninstallDisplayIcon={app}\jarvis\assets\jarvis.ico
UninstallDisplayName=Jarvis
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "autostart"; Description: "Jarvis mit Windows starten (im Infobereich neben der Uhr)"; GroupDescription: "Weitere Optionen:"

[InstallDelete]
; Reste der alten Version mit eigener Jarvis.exe (von Smart App Control blockiert)
Type: files; Name: "{app}\Jarvis.exe"
Type: filesandordirs; Name: "{app}\_internal"
; Alte Programmdateien ersetzen (Einstellungen liegen woanders und bleiben)
Type: filesandordirs; Name: "{app}\python"
Type: filesandordirs; Name: "{app}\jarvis"

[Files]
Source: "build\app\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Jarvis"; Filename: "{#Launcher}"; Parameters: """{#Script}"""; WorkingDir: "{app}\jarvis"; IconFilename: "{app}\jarvis\assets\jarvis.ico"
Name: "{group}\Jarvis deinstallieren"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Jarvis"; Filename: "{#Launcher}"; Parameters: """{#Script}"""; WorkingDir: "{app}\jarvis"; IconFilename: "{app}\jarvis\assets\jarvis.ico"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Jarvis"; ValueData: """{#Launcher}"" ""{#Script}"" --minimized"; Tasks: autostart
; Ohne Autostart: einen alten Eintrag (zeigte auf die blockierte Jarvis.exe) entfernen
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "Jarvis"; Flags: deletevalue; Tasks: not autostart
; Beim Deinstallieren immer entfernen (auch wenn im Programm gesetzt)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "Jarvis"; Flags: uninsdeletevalue

[Run]
; Laufendes (altes) Jarvis vor dem ersten Start beenden
Filename: "{app}\python\python.exe"; Parameters: """{#Script}"" --quit"; Flags: runhidden waituntilterminated
Filename: "{#Launcher}"; Parameters: """{#Script}"""; WorkingDir: "{app}\jarvis"; Description: "Jarvis jetzt starten"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\python\python.exe"; Parameters: """{#Script}"" --quit"; Flags: runhidden waituntilterminated; RunOnceId: "StopJarvis"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\python"
Type: filesandordirs; Name: "{app}\jarvis"

; Einstellungen und Verlauf in %APPDATA%\Jarvis bleiben beim Deinstallieren erhalten.
