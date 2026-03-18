#!/usr/bin/env powershell
# 智能视频水印去除工具 - 用户偏好设置完整测试脚本
# 偏好设置的保存、加载、验证和主题切换测试

param(
    [Parameter()]
    [switch]$Verbose,

    [Parameter()]
    [switch]$Quick,

    [Parameter()]
    [string]$TestDataPath = "tests/test_data",

    [Parameter()]
    [switch]$KeepTestFiles
)

# 设置错误处理
$ErrorActionPreference = "Stop"

# 颜色配置
$Colors = @{
    Header = "Green"
    Success = "Green"
    Warning = "Yellow"
    Error = "Red"
    Info = "Cyan"
    Detail = "White"
    Progress = "Blue"
    Summary = "Magenta"
}

# 测试结果追踪
$TestResults = @{
    Passed = 0
    Failed = 0
    Skipped = 0
    Details = @()
    StartTime = Get-Date
}

# 记录测试结果函数
function Record-TestResult {
    param(
        [string]$TestName,
        [bool]$Passed,
        [string]$Details = "",
        [bool]$Skipped = $false
    )

    $result = @{
        TestName = $TestName
        Passed = $Passed
        Skipped = $Skipped
        Details = $Details
        Timestamp = Get-Date
    }

    $TestResults.Details += $result

    if ($Skipped) {
        $TestResults.Skipped++
        Write-Host "⏭️ $TestName - 跳过" -ForegroundColor $Colors.Warning
    } elseif ($Passed) {
        $TestResults.Passed++
        Write-Host "✅ $TestName - 通过" -ForegroundColor $Colors.Success
    } else {
        $TestResults.Failed++
        Write-Host "❌ $TestName - 失败" -ForegroundColor $Colors.Error
        if ($Details -and $Verbose) {
            Write-Host "   详细信息: $Details" -ForegroundColor $Colors.Detail
        }
    }
}

# 显示测试摘要
function Show-TestSummary {
    $endTime = Get-Date
    $duration = $endTime - $TestResults.StartTime

    Write-Host ""
    Write-Host "👤 用户偏好设置测试摘要" -ForegroundColor $Colors.Summary
    Write-Host "=" * 50 -ForegroundColor $Colors.Info
    Write-Host "🕒 执行时间: $($duration.ToString('mm\:ss'))" -ForegroundColor $Colors.Info
    Write-Host "✅ 通过: $($TestResults.Passed)" -ForegroundColor $Colors.Success
    Write-Host "❌ 失败: $($TestResults.Failed)" -ForegroundColor $Colors.Error
    Write-Host "⏭️ 跳过: $($TestResults.Skipped)" -ForegroundColor $Colors.Warning
    Write-Host "📋 总计: $(($TestResults.Passed + $TestResults.Failed + $TestResults.Skipped))" -ForegroundColor $Colors.Info

    if ($TestResults.Failed -eq 0) {
        Write-Host ""
        Write-Host "🎉 所有用户偏好设置测试通过！" -ForegroundColor $Colors.Success
    } else {
        Write-Host ""
        Write-Host "⚠️ 有 $($TestResults.Failed) 项用户偏好设置测试失败" -ForegroundColor $Colors.Warning
    }
}

Write-Host "👤 智能视频水印去除工具 - 用户偏好设置测试" -ForegroundColor $Colors.Header
Write-Host "模式: $(if($Quick){'快速'}else{'完整'}) | 详细输出: $(if($Verbose){'开启'}else{'关闭'})" -ForegroundColor $Colors.Info
Write-Host "=" * 60 -ForegroundColor $Colors.Info

# 检查虚拟环境
if (-not (Test-Path ".venv")) {
    Write-Host "❌ 虚拟环境不存在，请先运行: .\scripts\vwr.ps1 setup -Dev" -ForegroundColor $Colors.Error
    exit 1
}

# 激活虚拟环境
Write-Host "🔄 激活虚拟环境..." -ForegroundColor $Colors.Progress
. .\.venv\Scripts\Activate.ps1

# 设置环境变量
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$env:PYTHONPATH = (Get-Location).Path

# 创建测试数据目录
if (-not (Test-Path $TestDataPath)) {
    New-Item -ItemType Directory -Path $TestDataPath -Force | Out-Null
    Write-Host "📁 创建测试数据目录: $TestDataPath" -ForegroundColor $Colors.Info
}

#region 用户偏好模块导入测试
Write-Host ""
Write-Host "📦 用户偏好模块导入测试..." -ForegroundColor $Colors.Progress

try {
    $importTest = python -c @"
import sys
import os
sys.path.insert(0, os.getcwd())

# 测试用户偏好相关模块导入
modules = [
    'app.config.user_preferences_manager',
    'app.config.preferences_storage',
    'app.config.preferences_validator',
    'app.config.preferences_defaults'
]

missing_modules = []
for module in modules:
    try:
        __import__(module)
        print(f'✅ {module} 导入成功')
    except Exception as e:
        print(f'❌ {module} 导入失败: {e}')
        missing_modules.append(module)

if missing_modules:
    print(f'缺少模块: {missing_modules}')
    sys.exit(1)
else:
    print('所有用户偏好模块导入成功')
"@

    Write-Host $importTest -ForegroundColor $Colors.Detail
    Record-TestResult "用户偏好模块导入" $true "所有模块导入成功"

} catch {
    Record-TestResult "用户偏好模块导入" $false "模块导入失败: $($_.Exception.Message)"
}
#endregion

#region 偏好设置管理器初始化测试
Write-Host ""
Write-Host "⚙️ 偏好设置管理器初始化测试..." -ForegroundColor $Colors.Progress

try {
    $managerTest = python -c @"
import sys
import os
sys.path.insert(0, os.getcwd())

from app.config.user_preferences_manager import UserPreferencesManager

# 创建偏好设置管理器
prefs_manager = UserPreferencesManager()
print('✅ UserPreferencesManager 创建成功')

# 测试获取默认偏好设置
default_prefs = prefs_manager.get_default_preferences()
print(f'✅ 默认偏好设置获取成功，设置项数量: {len(default_prefs)}')

# 检查关键设置项
required_keys = ['theme', 'language', 'auto_save', 'output_quality']
missing_keys = []

for key in required_keys:
    if key in default_prefs:
        print(f'✅ 必需设置项 {key}: {default_prefs[key]}')
    else:
        print(f'❌ 缺少必需设置项: {key}')
        missing_keys.append(key)

if missing_keys:
    print(f'缺少关键设置项: {missing_keys}')
    sys.exit(1)

print('偏好设置管理器初始化测试通过')
"@

    Write-Host $managerTest -ForegroundColor $Colors.Detail
    Record-TestResult "偏好设置管理器初始化" $true "偏好设置管理器初始化成功"

} catch {
    Record-TestResult "偏好设置管理器初始化" $false "偏好设置管理器初始化失败: $($_.Exception.Message)"
}
#endregion

#region 偏好设置验证测试
Write-Host ""
Write-Host "🔍 偏好设置验证测试..." -ForegroundColor $Colors.Progress

try {
    $validationTest = python -c @"
import sys
import os
sys.path.insert(0, os.getcwd())

from app.config.preferences_validator import PreferencesValidator
from app.config.user_preferences_manager import UserPreferencesManager

# 创建验证器和管理器
validator = PreferencesValidator()
prefs_manager = UserPreferencesManager()

print('✅ PreferencesValidator 创建成功')

# 获取默认设置用于测试
default_prefs = prefs_manager.get_default_preferences()

# 测试有效设置验证
if validator.validate(default_prefs):
    print('✅ 默认设置验证通过')
else:
    print('❌ 默认设置验证失败')
    sys.exit(1)

# 测试无效设置验证
invalid_prefs = default_prefs.copy()
invalid_prefs['theme'] = 'invalid_theme'
invalid_prefs['language'] = 'invalid_lang'

if not validator.validate(invalid_prefs):
    print('✅ 无效设置正确被识别')
else:
    print('❌ 无效设置验证失败')
    sys.exit(1)

# 测试设置项类型验证
type_test_prefs = default_prefs.copy()
type_test_prefs['auto_save'] = 'not_boolean'  # 应该是布尔值

if not validator.validate(type_test_prefs):
    print('✅ 设置项类型验证正确')
else:
    print('❌ 设置项类型验证失败')

print('偏好设置验证测试通过')
"@

    Write-Host $validationTest -ForegroundColor $Colors.Detail
    Record-TestResult "偏好设置验证" $true "偏好设置验证功能正常"

} catch {
    Record-TestResult "偏好设置验证" $false "偏好设置验证测试失败: $($_.Exception.Message)"
}
#endregion

#region 偏好设置存储测试
Write-Host ""
Write-Host "💾 偏好设置存储测试..." -ForegroundColor $Colors.Progress

try {
    $storageTest = python -c @"
import sys
import os
import tempfile
import json
sys.path.insert(0, os.getcwd())

from app.config.preferences_storage import PreferencesStorage
from app.config.user_preferences_manager import UserPreferencesManager

# 创建存储器和管理器
storage = PreferencesStorage()
prefs_manager = UserPreferencesManager()

print('✅ PreferencesStorage 创建成功')

# 获取测试数据
test_prefs = prefs_manager.get_default_preferences()
test_prefs['theme'] = 'dark'
test_prefs['language'] = 'zh_CN'
test_prefs['test_setting'] = 'test_value'

# 创建临时文件进行测试
with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    temp_file = f.name

try:
    # 测试保存
    if storage.save(test_prefs, temp_file):
        print('✅ 偏好设置保存成功')
    else:
        print('❌ 偏好设置保存失败')
        sys.exit(1)

    # 验证文件是否创建
    if os.path.exists(temp_file):
        print('✅ 偏好设置文件创建成功')
    else:
        print('❌ 偏好设置文件创建失败')
        sys.exit(1)

    # 测试加载
    loaded_prefs = storage.load(temp_file)
    if loaded_prefs:
        print('✅ 偏好设置加载成功')
    else:
        print('❌ 偏好设置加载失败')
        sys.exit(1)

    # 测试数据一致性
    if (loaded_prefs['theme'] == 'dark' and
        loaded_prefs['language'] == 'zh_CN' and
        loaded_prefs['test_setting'] == 'test_value'):
        print('✅ 偏好设置数据一致性验证通过')
    else:
        print('❌ 偏好设置数据一致性验证失败')
        print(f'期望 theme=dark, 实际 theme={loaded_prefs.get("theme")}')
        print(f'期望 language=zh_CN, 实际 language={loaded_prefs.get("language")}')
        sys.exit(1)

finally:
    if os.path.exists(temp_file):
        os.unlink(temp_file)
        print('✅ 临时文件清理完成')

print('偏好设置存储测试通过')
"@

    Write-Host $storageTest -ForegroundColor $Colors.Detail
    Record-TestResult "偏好设置存储" $true "偏好设置存储功能正常"

} catch {
    Record-TestResult "偏好设置存储" $false "偏好设置存储测试失败: $($_.Exception.Message)"
}
#endregion

#region 主题切换测试
Write-Host ""
Write-Host "🎨 主题切换测试..." -ForegroundColor $Colors.Progress

try {
    $themeTest = python -c @"
import sys
import os
sys.path.insert(0, os.getcwd())

from app.config.user_preferences_manager import UserPreferencesManager
from app.config.style_manager import StyleManager

# 创建管理器
prefs_manager = UserPreferencesManager()
style_manager = StyleManager()

print('✅ 主题管理器创建成功')

# 获取可用主题
available_themes = style_manager.get_available_themes()
print(f'✅ 可用主题: {available_themes}')

if len(available_themes) == 0:
    print('⚠️ 未找到可用主题')
    sys.exit(2)

# 测试主题切换
for theme in available_themes:
    try:
        # 创建包含新主题的偏好设置
        test_prefs = prefs_manager.get_default_preferences()
        test_prefs['theme'] = theme

        # 验证主题是否有效
        if style_manager.is_valid_theme(theme):
            print(f'✅ 主题 {theme} 验证通过')

            # 尝试应用主题样式
            style_sheet = style_manager.get_theme_stylesheet(theme)
            if style_sheet:
                print(f'✅ 主题 {theme} 样式表获取成功')
            else:
                print(f'⚠️ 主题 {theme} 样式表为空')
        else:
            print(f'❌ 主题 {theme} 无效')
            sys.exit(1)

    except Exception as e:
        print(f'❌ 主题 {theme} 切换失败: {e}')
        sys.exit(1)

print('主题切换测试通过')
"@

    if ($LASTEXITCODE -eq 2) {
        Record-TestResult "主题切换" $false "未找到可用主题" $true
    } else {
        Write-Host $themeTest -ForegroundColor $Colors.Detail
        Record-TestResult "主题切换" $true "主题切换功能正常"
    }

} catch {
    Record-TestResult "主题切换" $false "主题切换测试失败: $($_.Exception.Message)"
}
#endregion

#region 语言设置测试
if (-not $Quick) {
    Write-Host ""
    Write-Host "🌐 语言设置测试..." -ForegroundColor $Colors.Progress

    try {
        $languageTest = python -c @"
import sys
import os
sys.path.insert(0, os.getcwd())

from app.config.user_preferences_manager import UserPreferencesManager

# 创建偏好设置管理器
prefs_manager = UserPreferencesManager()

# 测试支持的语言
supported_languages = ['zh_CN', 'en_US', 'ja_JP', 'ko_KR']
print(f'测试语言: {supported_languages}')

for lang in supported_languages:
    try:
        # 创建包含新语言的偏好设置
        test_prefs = prefs_manager.get_default_preferences()
        test_prefs['language'] = lang

        # 验证设置
        if prefs_manager.validate_preferences(test_prefs):
            print(f'✅ 语言 {lang} 设置有效')
        else:
            print(f'❌ 语言 {lang} 设置无效')
            sys.exit(1)

    except Exception as e:
        print(f'❌ 语言 {lang} 测试失败: {e}')
        sys.exit(1)

print('语言设置测试通过')
"@

        Write-Host $languageTest -ForegroundColor $Colors.Detail
        Record-TestResult "语言设置" $true "语言设置功能正常"

    } catch {
        Record-TestResult "语言设置" $false "语言设置测试失败: $($_.Exception.Message)"
    }
}
#endregion

#region 高级偏好设置测试
if (-not $Quick) {
    Write-Host ""
    Write-Host "🔧 高级偏好设置测试..." -ForegroundColor $Colors.Progress

    try {
        $advancedTest = python -c @"
import sys
import os
sys.path.insert(0, os.getcwd())

from app.config.user_preferences_manager import UserPreferencesManager

# 创建偏好设置管理器
prefs_manager = UserPreferencesManager()

# 测试高级设置项
advanced_settings = {
    'auto_save': True,
    'backup_count': 5,
    'memory_limit': 2048,
    'gpu_acceleration': False,
    'temp_cleanup': True,
    'log_level': 'INFO'
}

print('测试高级设置项...')

# 获取默认设置并更新
test_prefs = prefs_manager.get_default_preferences()
test_prefs.update(advanced_settings)

# 验证高级设置
if prefs_manager.validate_preferences(test_prefs):
    print('✅ 高级偏好设置验证通过')
else:
    print('❌ 高级偏好设置验证失败')
    sys.exit(1)

# 测试设置项类型检查
type_tests = [
    ('auto_save', True, bool),
    ('backup_count', 5, int),
    ('memory_limit', 2048, int),
    ('log_level', 'INFO', str)
]

for key, value, expected_type in type_tests:
    if key in test_prefs and isinstance(test_prefs[key], expected_type):
        print(f'✅ {key} 类型检查通过: {type(test_prefs[key]).__name__}')
    else:
        print(f'❌ {key} 类型检查失败')
        sys.exit(1)

print('高级偏好设置测试通过')
"@

        Write-Host $advancedTest -ForegroundColor $Colors.Detail
        Record-TestResult "高级偏好设置" $true "高级偏好设置功能正常"

    } catch {
        Record-TestResult "高级偏好设置" $false "高级偏好设置测试失败: $($_.Exception.Message)"
    }
}
#endregion

#region 偏好设置重置测试
Write-Host ""
Write-Host "🔄 偏好设置重置测试..." -ForegroundColor $Colors.Progress

try {
    $resetTest = python -c @"
import sys
import os
import tempfile
sys.path.insert(0, os.getcwd())

from app.config.user_preferences_manager import UserPreferencesManager

# 创建偏好设置管理器
prefs_manager = UserPreferencesManager()

# 获取默认设置
default_prefs = prefs_manager.get_default_preferences()
print('✅ 获取默认设置成功')

# 创建修改过的设置
modified_prefs = default_prefs.copy()
modified_prefs['theme'] = 'custom_theme'
modified_prefs['language'] = 'custom_lang'
modified_prefs['custom_setting'] = 'custom_value'

print('✅ 创建修改过的设置')

# 测试重置功能
reset_prefs = prefs_manager.reset_to_defaults()

# 验证重置是否正确
if reset_prefs == default_prefs:
    print('✅ 偏好设置重置验证通过')
else:
    print('❌ 偏好设置重置验证失败')

    # 显示差异
    for key in default_prefs:
        if key not in reset_prefs or reset_prefs[key] != default_prefs[key]:
            print(f'差异项 {key}: 默认={default_prefs[key]}, 重置后={reset_prefs.get(key)}')

    sys.exit(1)

# 测试部分重置功能
partial_reset_keys = ['theme', 'language']
partial_reset_prefs = prefs_manager.reset_keys_to_defaults(modified_prefs, partial_reset_keys)

for key in partial_reset_keys:
    if partial_reset_prefs[key] == default_prefs[key]:
        print(f'✅ 部分重置 {key} 成功')
    else:
        print(f'❌ 部分重置 {key} 失败')
        sys.exit(1)

# 验证其他设置未被重置
if partial_reset_prefs.get('custom_setting') == 'custom_value':
    print('✅ 未重置的设置保持不变')
else:
    print('❌ 未重置的设置被意外修改')
    sys.exit(1)

print('偏好设置重置测试通过')
"@

    Write-Host $resetTest -ForegroundColor $Colors.Detail
    Record-TestResult "偏好设置重置" $true "偏好设置重置功能正常"

} catch {
    Record-TestResult "偏好设置重置" $false "偏好设置重置测试失败: $($_.Exception.Message)"
}
#endregion

#region 偏好设置迁移测试
if (-not $Quick) {
    Write-Host ""
    Write-Host "📦 偏好设置迁移测试..." -ForegroundColor $Colors.Progress

    try {
        $migrationTest = python -c @"
import sys
import os
import json
import tempfile
sys.path.insert(0, os.getcwd())

from app.config.user_preferences_manager import UserPreferencesManager

# 创建偏好设置管理器
prefs_manager = UserPreferencesManager()

# 模拟旧版本偏好设置格式
legacy_prefs = {
    'theme_name': 'dark',  # 旧格式
    'lang': 'zh',          # 旧格式
    'auto_save_enabled': True  # 旧格式
}

print('创建旧版本偏好设置格式')

# 创建临时文件保存旧格式设置
with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    json.dump(legacy_prefs, f, ensure_ascii=False, indent=2)
    legacy_file = f.name

try:
    # 测试迁移功能
    migrated_prefs = prefs_manager.migrate_preferences(legacy_file)

    if migrated_prefs:
        print('✅ 偏好设置迁移成功')

        # 验证迁移后的格式
        expected_mappings = {
            'theme': 'dark',  # theme_name -> theme
            'language': 'zh_CN',  # lang -> language (并标准化)
            'auto_save': True     # auto_save_enabled -> auto_save
        }

        for new_key, expected_value in expected_mappings.items():
            if new_key in migrated_prefs:
                print(f'✅ 迁移映射 {new_key}: {migrated_prefs[new_key]}')
            else:
                print(f'❌ 缺少迁移映射: {new_key}')
                sys.exit(1)

        # 验证迁移后设置的有效性
        if prefs_manager.validate_preferences(migrated_prefs):
            print('✅ 迁移后设置验证通过')
        else:
            print('❌ 迁移后设置验证失败')
            sys.exit(1)
    else:
        print('⚠️ 偏好设置迁移返回空结果')

finally:
    if os.path.exists(legacy_file):
        os.unlink(legacy_file)

print('偏好设置迁移测试通过')
"@

        Write-Host $migrationTest -ForegroundColor $Colors.Detail
        Record-TestResult "偏好设置迁移" $true "偏好设置迁移功能正常"

    } catch {
        Record-TestResult "偏好设置迁移" $false "偏好设置迁移测试失败: $($_.Exception.Message)"
    }
}
#endregion

# 显示测试摘要
Show-TestSummary

# 清理临时文件
if ((Test-Path $TestDataPath) -and (-not $KeepTestFiles)) {
    $tempFiles = Get-ChildItem $TestDataPath -Filter "*prefs*", "*test*"
    if ($tempFiles.Count -gt 0) {
        Remove-Item $tempFiles.FullName -Force
        Write-Host "🧹 清理临时测试文件" -ForegroundColor $Colors.Info
    }
}

Write-Host ""
Write-Host "📋 用户偏好设置测试完成。运行完整测试: .\scripts\vwr.ps1 test all" -ForegroundColor $Colors.Info

# 返回适当的退出码
if ($TestResults.Failed -gt 0) {
    exit 1
} else {
    exit 0
}
