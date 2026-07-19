; AI Talking Tom - Inno Setup Installer Script
; Compile with Inno Setup Compiler (https://jrsoftware.org/isinfo.php)

#define MyAppName "AI Talking Tom"
#define MyAppVersion "1.0"
#define MyAppPublisher "AI Talking Tom"
#define MyAppURL "https://github.com/mccool1010/AI_talking_tom_V1"
#define MyAppExeName "run.bat"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=Output
OutputBaseFilename=AI_Talking_Tom_Setup_v{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
LicenseFile=..\license.txt

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Launcher + Model Downloader
Source: "..\launcher.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\run.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\download_models.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion

; Backend Python code
Source: "..\backend\*.py"; DestDir: "{app}\backend"; Flags: ignoreversion
Source: "..\backend\app\*"; DestDir: "{app}\backend\app"; Flags: ignoreversion recursesubdirs

; Godot project
Source: "..\godot\project.godot"; DestDir: "{app}\godot"; Flags: ignoreversion
Source: "..\godot\scenes\*"; DestDir: "{app}\godot\scenes"; Flags: ignoreversion recursesubdirs
Source: "..\godot\scripts\*"; DestDir: "{app}\godot\scripts"; Flags: ignoreversion recursesubdirs
Source: "..\godot\models\*.glb"; DestDir: "{app}\godot\models"; Flags: ignoreversion
Source: "..\godot\models\*.png"; DestDir: "{app}\godot\models"; Flags: ignoreversion
Source: "..\godot\models\*.jpg"; DestDir: "{app}\godot\models"; Flags: ignoreversion
Source: "..\godot\models\*.import"; DestDir: "{app}\godot\models"; Flags: ignoreversion

; Piper TTS engine + DLLs
Source: "..\piper\*"; DestDir: "{app}\piper"; Flags: ignoreversion recursesubdirs

; TTS voice model
Source: "..\models\tts\*"; DestDir: "{app}\models\tts"; Flags: ignoreversion recursesubdirs

; Vosk STT model (test only but included for completeness)
Source: "..\models\vosk\*"; DestDir: "{app}\models\vosk"; Flags: ignoreversion recursesubdirs

; YOLOv8 model
Source: "..\yolov8n.pt"; DestDir: "{app}"; Flags: ignoreversion

; Textures
Source: "..\textures\*"; DestDir: "{app}\textures"; Flags: ignoreversion

; Dashboard
Source: "..\dashboard\index.html"; DestDir: "{app}\dashboard"; Flags: ignoreversion
Source: "..\dashboard\src\*"; DestDir: "{app}\dashboard\src"; Flags: ignoreversion recursesubdirs
Source: "..\dashboard\public\*"; DestDir: "{app}\dashboard\public"; Flags: ignoreversion recursesubdirs
Source: "..\dashboard\package.json"; DestDir: "{app}\dashboard"; Flags: ignoreversion
Source: "..\dashboard\vite.config.js"; DestDir: "{app}\dashboard"; Flags: ignoreversion

; License + Docs
Source: "..\license.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion

; NOTE: LLM model (qwen2.5-3b-instruct-q4_k_m.gguf, ~2GB) is NOT included.
; Users must run: python download_models.py

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\run.bat"
Name: "{group}\Download AI Models"; Filename: "cmd.exe"; Parameters: "/k cd /d ""{app}"" && python download_models.py"; WorkingDir: "{app}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\run.bat"; Tasks: desktopicon

[Run]
Filename: "{app}\run.bat"; Description: "Launch AI Talking Tom"; Flags: nowait postinstall skipifsilent shellexec

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    MsgBox('Installation complete!' + #13#10 + #13#10 +
           'BEFORE RUNNING, you need to:' + #13#10 + #13#10 +
           '1. Install Python 3.10+ (python.org)' + #13#10 +
           '2. Install Godot 4.6 (godotengine.org)' + #13#10 +
           '3. Install MongoDB (mongodb.com)' + #13#10 +
           '4. Open a terminal in the install folder and run:' + #13#10 +
           '   python -m venv venv' + #13#10 +
           '   venv\Scripts\activate' + #13#10 +
           '   pip install -r requirements.txt' + #13#10 +
           '   python download_models.py' + #13#10 + #13#10 +
           'The LLM model (~2 GB) will be downloaded from HuggingFace.' + #13#10 +
           'Other AI models (Whisper, DeepFace) auto-download on first run.' + #13#10 + #13#10 +
           'See README.md for full details.',
           mbInformation, MB_OK);
  end;
end;
