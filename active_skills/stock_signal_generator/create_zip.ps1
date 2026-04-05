# 创建 CoPaw Skill ZIP 包

$skill_path = "E:\pycharm\stock-analysis\active_skills\stock_signal_generator"
$output_zip = "E:\pycharm\stock-analysis\active_skills\stock_signal_generator.zip"

# 获取所有文件（包括隐藏文件）
$files = Get-ChildItem -Path $skill_path -Force -File

# 创建临时文件列表
$file_list = New-Object System.Collections.Generic.List[string]
foreach ($file in $files) {
    $file_list.Add($file.FullName)
}

# 使用 7-Zip 创建 ZIP（如果安装了 7-Zip）
$sevenzip = "C:\Program Files\7-Zip\7z.exe"
if (Test-Path $sevenzip) {
    Write-Host "使用 7-Zip 创建 ZIP..."
    & $sevenzip a -tzip $output_zip $file_list.ToArray()
} else {
    Write-Host "未找到 7-Zip，使用 PowerShell Compress-Archive..."
    Compress-Archive -Path $file_list.ToArray() -DestinationPath $output_zip -Force
}

Write-Host "✅ ZIP 包创建完成: $output_zip"
Write-Host "📁 包含文件: $($file_list.Count)"
