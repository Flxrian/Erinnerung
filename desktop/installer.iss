; Inno-Setup-Skript für Jarvis-Setup.exe
; Bauen (nach PyInstaller):  ISCC.exe /DAppVersion=3.0.0 installer.iss

#ifndef AppVersion
  #define AppVersion "3.0.0"
#endif

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
UninstallDisplayIcon={app}\Jarvis.exe
UninstallDisplayName=Jarvis
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=force

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "autostart"; Description: "Jarvis mit Windows starten (im Infobereich neben der Uhr)"; GroupDescription: "Weitere Optionen:"

[Files]
Source: "dist\Jarvis\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Jarvis"; Filename: "{app}\Jarvis.exe"
Name: "{group}\Jarvis deinstallieren"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Jarvis"; Filename: "{app}\Jarvis.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Jarvis"; ValueData: """{app}\Jarvis.exe"" --minimized"; Tasks: autostart
; Autostart-Eintrag beim Deinstallieren immer entfernen (auch wenn er im Programm gesetzt wurde)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "Jarvis"; Flags: uninsdeletevalue

[Run]
Filename: "{app}\Jarvis.exe"; Description: "Jarvis jetzt starten"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM Jarvis.exe"; Flags: runhidden; RunOnceId: "StopJarvis"

; Einstellungen und Verlauf in %APPDATA%\Jarvis bleiben beim Deinstallieren erhalten.
