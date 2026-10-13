; BC.Transporter — script installer Inno Setup
; Compila con: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\BC-Transporter.iss
#define AppVersion "1.0.0"

[Setup]
AppId={{9AC1557F-13A4-4447-A062-BC489AF5F5CE}
AppName=BC.Transporter
AppVersion={#AppVersion}
AppPublisher=BC.Transporter
DefaultDirName={autopf}\BC.Transporter
DefaultGroupName=BC.Transporter
DisableProgramGroupPage=yes
OutputDir={#SourcePath}\out
OutputBaseFilename=BC-Transporter-Setup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
PrivilegesRequired=lowest
UninstallDisplayName=BC.Transporter

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#SourcePath}\..\dist\BC-Transporter.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourcePath}\..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourcePath}\..\README.en.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourcePath}\..\README.de.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourcePath}\..\README.fr.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\BC.Transporter"; Filename: "{app}\BC-Transporter.exe"
Name: "{autodesktop}\BC.Transporter"; Filename: "{app}\BC-Transporter.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\BC-Transporter.exe"; Description: "{cm:LaunchProgram,BC.Transporter}"; Flags: nowait postinstall skipifsilent
