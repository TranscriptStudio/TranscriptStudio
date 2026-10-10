; ============================================================
; Installateur Windows - Transcript Studio 1.0 (P11)
;
; Inno Setup 6, installation per-machine (Program Files, UAC).
;
; Compilation (Inno Setup 6 installe) :
;   ISCC.exe tools\installer_windows.iss
; Sortie : dist\TranscriptStudio-1.0-setup.exe
;
; Prerequis : le dossier build\TranscriptStudio.dist doit
; exister (produit par tools\build_windows.bat).
; ============================================================

#define MyAppName "Transcript Studio"
#define MyAppVersion "1.0"
#define MyAppPublisher "Transcript Studio"
#define MyAppExeName "TranscriptStudio.exe"
#define MyAppDir "..\build\TranscriptStudio.dist"

[Setup]
AppId={{2C80EDFA-94F2-4E3A-962E-08D70F0073F5}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
; Per-machine : Program Files, registre HKLM, UAC a l'installation
PrivilegesRequired=admin
OutputDir=..\dist
OutputBaseFilename=TranscriptStudio-1.0-setup
SetupIconFile=..\icons\icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
UninstallDisplayName={#MyAppName}

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le &bureau"; GroupDescription: "Raccourcis :"

[Files]
; Application standalone Nuitka complete : exe, DLL Qt,
; FFmpeg embarque, icones, manuel PDF
Source: "{#MyAppDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Manuel utilisateur"; Filename: "{app}\docs\Manuel utilisateur.pdf"
Name: "{group}\Désinstaller {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Lancer {#MyAppName}"; Flags: nowait postinstall skipifsilent
