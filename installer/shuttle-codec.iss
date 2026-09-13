; Inno Setup script for Shuttle Codec (Windows installer).
;
; Build it after `python build_exe.py` (which produces dist\shuttle-codec.exe):
;
;   iscc installer\shuttle-codec.iss /DMyAppVersion=1.3.1
;
; Optional code signing: pass a SignTool configured in Inno Setup, e.g.
;   iscc installer\shuttle-codec.iss /DMyAppVersion=1.3.1 /Ssigntool="signtool sign /f cert.pfx /p pass $f"
; See docs/RELEASING.md for the full release + signing checklist.

#define MyAppName "Shuttle Codec"
; Fallback only: the release workflow always passes /DMyAppVersion. It must match
; src/__init__.py, and tests/test_project_consistency.py enforces that.
#ifndef MyAppVersion
  #define MyAppVersion "1.3.1"
#endif
#define MyAppPublisher "JMarc"
#define MyAppURL "https://github.com/jmarc9901/shuttle-codec"
#define MyAppExeName "shuttle-codec.exe"

[Setup]
AppId={{8F1B1B3E-5C7A-4F2E-9D0B-2A7C4E9F1B10}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
OutputDir=..\dist
OutputBaseFilename=shuttle-codec-{#MyAppVersion}-setup
SetupIconFile=..\logo.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Requires a SignTool definition passed on the command line to sign the setup.
; SignTool=signtool

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
