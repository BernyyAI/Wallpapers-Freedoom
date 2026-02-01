[Setup]
AppName=Wallpaper Freedom
AppVersion=1.0
AppPublisher=BernyyAI
DefaultDirName={autopf}\Wallpaper Freedom
DefaultGroupName=Wallpaper Freedom
OutputDir=installer_output
OutputBaseFilename=WallpaperFreedom_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\Wallpaper Freedom.exe
ArchitecturesInstallIn64BitMode=x64
SetupIconFile=app\assets\ui\icon.ico

[Files]
Source: "dist\Wallpaper Freedom.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Wallpaper Freedom"; Filename: "{app}\Wallpaper Freedom.exe"
Name: "{autodesktop}\Wallpaper Freedom"; Filename: "{app}\Wallpaper Freedom.exe"; Tasks: desktopicon
Name: "{group}\Desinstalar Wallpaper Freedom"; Filename: "{uninstallexe}"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: checkedonce

[Run]
Filename: "{app}\Wallpaper Freedom.exe"; Description: "Ejecutar Wallpaper Freedom ahora"; Flags: nowait postinstall skipifsilent
