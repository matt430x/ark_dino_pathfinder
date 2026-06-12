#define AppName      "ARK Dino Pathfinder"
#ifndef AppVersion
  #error AppVersion must be supplied on the command line: /DAppVersion=x.x
#endif
#define AppPublisher "matt430"
#define AppURL       "https://github.com/matt430x/ark_dino_pathfinder"
#define AppExeName   "gui.exe"

[Setup]
AppId={{A3F2C1D4-8B6E-4F2A-9C7D-1E5B3A0F2D8C}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} v{#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases

; Install to user's local programs (no UAC prompt, allows self-update)
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
PrivilegesRequired=lowest

; Output
OutputDir=installer_output
OutputBaseFilename=ARKDinoPathfinder_Setup_v{#AppVersion}
SetupIconFile=

; Compression
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Main executable
Source: "dist\gui\gui.exe"; DestDir: "{app}"; Flags: ignoreversion

; All runtime dependencies (DLLs, Python stdlib, bundled models, etc.)
Source: "dist\gui\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu
Name: "{group}\{#AppName}";                       Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"

; Desktop (optional, off by default)
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall

[UninstallDelete]
; Clean up temp files written by the app next to the exe
Type: filesandordirs; Name: "{app}\*.old"
