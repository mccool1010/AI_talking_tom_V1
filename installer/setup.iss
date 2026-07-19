; AI Talking Tom - Inno Setup Installer Script
; Compile with Inno Setup Compiler (https://jrsoftware.org/isinfo.php)

#define MyAppName "AI Talking Tom"
#define MyAppVersion "1.0"
#define MyAppPublisher "AI Talking Tom"
#define MyAppURL "https://github.com/mccool1010/AI_talking_tom_V1"
#define MyAppExeName "launcher.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=installer\Output
OutputBaseFilename=AI_Talking_Tom_Setup_v{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
LicenseFile=license.txt

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Launcher
Source: "launcher.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "run.bat"; DestDir: "{app}"; Flags: ignoreversion

; Backend Python code
Source: "backend\*.py"; DestDir: "{app}\backend"; Flags: ignoreversion recursesubdirs
Source: "backend\app\*"; DestDir: "{app}\backend\app"; Flags: ignoreversion recursesubdirs

; Godot project
Source: "godot\project.godot"; DestDir: "{app}\godot"; Flags: ignoreversion
Source: "godot\scenes\*"; DestDir: "{app}\godot\scenes"; Flags: ignoreversion recursesubdirs
Source: "godot\scripts\*"; DestDir: "{app}\godot\scripts"; Flags: ignoreversion recursesubdirs
Source: "godot\models\*.glb"; DestDir: "{app}\godot\models"; Flags: ignoreversion
Source: "godot\models\*.png"; DestDir: "{app}\godot\models"; Flags: ignoreversion
Source: "godot\models\*.jpg"; DestDir: "{app}\godot\models"; Flags: ignoreversion

; Piper TTS
Source: "piper\*"; DestDir: "{app}\piper"; Flags: ignoreversion recursesubdirs

; ML models
Source: "yolov8n.pt"; DestDir: "{app}"; Flags: ignoreversion

; Dashboard
Source: "dashboard\index.html"; DestDir: "{app}\dashboard"; Flags: ignoreversion
Source: "dashboard\src\*"; DestDir: "{app}\dashboard\src"; Flags: ignoreversion recursesubdirs
Source: "dashboard\public\*"; DestDir: "{app}\dashboard\public"; Flags: ignoreversion recursesubdirs
Source: "dashboard\package.json"; DestDir: "{app}\dashboard"; Flags: ignoreversion
Source: "dashboard\vite.config.js"; DestDir: "{app}\dashboard"; Flags: ignoreversion

; Requirements
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion

; License
Source: "license.txt"; DestDir: "{app}"; Flags: ignoreversion

; Docs
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\run.bat"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\run.bat"; Tasks: desktopicon

[Run]
Filename: "{app}\run.bat"; Description: "Launch AI Talking Tom"; Flags: nowait postinstall skipifsilent shellexec

[Code]
// Post-install: remind user to install Python dependencies
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    MsgBox('Installation complete!' + #13#10 + #13#10 +
           'Before running, make sure you have:' + #13#10 +
           '1. Python 3.10+ installed' + #13#10 +
           '2. Godot 4.6 installed' + #13#10 +
           '3. Run: pip install -r requirements.txt' + #13#10 + #13#10 +
           'See README.md for full setup instructions.',
           mbInformation, MB_OK);
  end;
end;
