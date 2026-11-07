; Inno Setup script for Eye Care (per-user install, no admin rights needed).
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{8D1F6C2A-5B7E-4E39-A4C1-7E2B9D0F3A61}
AppName=Eye Care
AppVersion={#AppVersion}
AppPublisher=imhamiddev
AppPublisherURL=https://github.com/imhamiddev/Eyes-protect
DefaultDirName={autopf}\Eye Care
DefaultGroupName=Eye Care
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist-installer
OutputBaseFilename=EyeCare-Setup
SetupIconFile=..\eyecare\assets\eyecare.ico
UninstallDisplayIcon={app}\EyeCare.exe
UninstallDisplayName=Eye Care
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
AppMutex=EyeCareSingleInstanceMutex
CloseApplications=force
RestartApplications=no
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; Flags: unchecked

[Files]
Source: "..\dist\EyeCare\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\Eye Care"; Filename: "{app}\EyeCare.exe"
Name: "{autodesktop}\Eye Care"; Filename: "{app}\EyeCare.exe"; Tasks: desktopicon

[Registry]
; The app registers its own autostart entry; make sure uninstalling removes it.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "EyeCare"; Flags: uninsdeletevalue

[Run]
Filename: "{app}\EyeCare.exe"; Description: "Launch Eye Care"; Flags: nowait postinstall skipifsilent
