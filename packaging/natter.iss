; Windows installer for Natter (Inno Setup 6). Built by `python scripts/build.py --installer`,
; which passes AppVersion, Publisher, Homepage, SourceDir (the PyInstaller folder build),
; IconFile and OutputDir with /D.
;
; Installs for the current user by default (no admin prompt). Your WhatsApp session and
; settings live in AppData, so upgrading or uninstalling doesn't log you out.

#define AppName "Natter"
#define AppExe "Natter.exe"

[Setup]
; Never change AppId: Windows uses it to recognise upgrades of the same app.
AppId={{8A41B7D0-13ED-40B1-A3DA-A5BCFA0C1DF7}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#Publisher}
AppPublisherURL={#Homepage}
AppSupportURL={#Homepage}/issues
AppUpdatesURL={#Homepage}/releases
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#Publisher}
VersionInfoDescription={#AppName} setup
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile={#IconFile}
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes
; Natter keeps running in the tray: close it for the upgrade, then start it again.
CloseApplications=yes
RestartApplications=yes
OutputDir={#OutputDir}
OutputBaseFilename=Natter-{#AppVersion}-windows-x64-setup

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; Drop files from the previous version's folder build before copying the new one.
Type: filesandordirs; Name: "{app}\_internal"

[Registry]
; Natter adds itself to the login Run key when "Start on login" is on; remove that entry on
; uninstall so Windows doesn't try to start a program that's gone.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "{#AppName}"; Flags: uninsdeletevalue dontcreatekey

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
