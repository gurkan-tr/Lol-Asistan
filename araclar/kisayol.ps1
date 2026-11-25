param([string]$Pythonw, [string]$Klasor)
$Klasor = (Resolve-Path $Klasor).Path
$kabuk = New-Object -ComObject WScript.Shell
foreach ($hedef in @([Environment]::GetFolderPath("Desktop"), [Environment]::GetFolderPath("Programs"))) {
    $k = $kabuk.CreateShortcut((Join-Path $hedef "LoL Asistan.lnk"))
    $k.TargetPath = $Pythonw
    $k.Arguments = '"' + (Join-Path $Klasor "LoLAsistan.pyw") + '"'
    $k.WorkingDirectory = $Klasor
    $k.IconLocation = (Join-Path $Klasor "ikon.ico")
    $k.Description = "LoL Asistan"
    $k.Save()
}
