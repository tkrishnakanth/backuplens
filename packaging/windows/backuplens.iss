; BackupLens Windows installer — per-user, no administrator required.
; Build from the repository root after PyInstaller:
;   ISCC.exe /DMyAppVersion=0.1.0 packaging\windows\backuplens.iss
#define MyAppName "BackupLens"
#ifndef MyAppVersion
#define MyAppVersion "0.1.0"
#endif
#define MyAppPublisher "BackupLens contributors"
#define MyAppURL "https://github.com/tkrishnakanth/backuplens"
#define MyAppExeName "BackupLens.exe"
#define MyAppId "{{7B9C4E2A-6D31-4E7A-9F2B-2C5D8A1E4F60}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={localappdata}\Programs\BackupLens
DefaultGroupName=BackupLens
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\..\dist\installer
OutputBaseFilename=BackupLens-{#MyAppVersion}-windows-x64-setup
SetupIconFile=..\icon\icon.ico
LicenseFile=..\..\LICENSE
InfoBeforeFile=..\..\THIRD_PARTY_NOTICES.txt
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=BackupLens installer
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\..\dist\BackupLens\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\BackupLens"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\BackupLens"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch BackupLens"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if not UninstallSilent then
    begin
      DataDir := ExpandConstant('{localappdata}\BackupLens');
      if MsgBox('Delete BackupLens settings and cache from ' + DataDir + '?', mbConfirmation, MB_YESNO) = IDYES then
        DelTree(DataDir, True, True, True);
    end;
  end;
end;
