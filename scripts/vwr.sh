#!/usr/bin/env bash
set -Eeuo pipefail

# 智能视频水印去除工具的 Bash 交互式入口。
# 目标是与 scripts/vwr.ps1 保持相同的用户可见菜单和主要工程任务。

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

DEV=0
PYTHON_SELECTOR="3.12.10"
TORCH_BACKEND="auto"
DEFAULT_INDEX=""
DEFAULT_INDEX_BOUND=0
INDEX_STRATEGY="first-index"
AUTO_FIX=0
SKIP_CHECKS=0
CHECK="all"
FIX=0
QUICK=0
TEST_TYPE="all"
COVERAGE=0
PERFORMANCE=0
REPORT=0
FAIL_ON_LOW=0
MIN_COVERAGE=80
OPEN_REPORT=0
ITERATIONS=3
GPU_PROFILE=0
MEMORY_PROFILE=0
PERF_REPORT_PATH=""
SKIP_TESTS=0
CLEAN_SCOPE="all"
SKIP_COVERAGE=0
SKIP_PERFORMANCE=0
TIMEOUT_MINUTES=30
ARTIFACTS_DIR="logs/ci-artifacts"
OUTPUT_FILE=""
VWR_LOG_FILE=""
UV_EXECUTABLE=""

if [[ -t 1 ]]; then
  COLOR_CYAN=$'\033[36m'
  COLOR_GREEN=$'\033[32m'
  COLOR_YELLOW=$'\033[33m'
  COLOR_RED=$'\033[31m'
  COLOR_RESET=$'\033[0m'
else
  COLOR_CYAN=""
  COLOR_GREEN=""
  COLOR_YELLOW=""
  COLOR_RED=""
  COLOR_RESET=""
fi

log_line() {
  local level="$1"
  local message="$2"
  if [[ -n "${VWR_LOG_FILE}" ]]; then
    mkdir -p "$(dirname "${VWR_LOG_FILE}")"
    printf '[%s] [%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "${level}" "${message}" >> "${VWR_LOG_FILE}"
  fi
}

write_line() {
  local color="$1"
  local prefix="$2"
  local level="$3"
  local message="$4"
  printf '%s%s%s%s\n' "${color}" "${prefix}" "${message}" "${COLOR_RESET}"
  log_line "${level}" "${message}"
}

info() { write_line "${COLOR_CYAN}" "[i] " "INFO" "$1"; }
ok() { write_line "${COLOR_GREEN}" "[OK] " "SUCCESS" "$1"; }
warn() { write_line "${COLOR_YELLOW}" "[!] " "WARNING" "$1"; }
err() { write_line "${COLOR_RED}" "[X] " "ERROR" "$1"; }
die() {
  err "$1"
  exit 1
}

section() {
  printf '\n%s============================================================%s\n' "${COLOR_CYAN}" "${COLOR_RESET}"
  printf '%s%s%s\n' "${COLOR_CYAN}" "$1" "${COLOR_RESET}"
  printf '%s============================================================%s\n' "${COLOR_CYAN}" "${COLOR_RESET}"
  log_line "SECTION" "$1"
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

initialize_log() {
  mkdir -p logs
  VWR_LOG_FILE="${PROJECT_ROOT}/logs/vwr_$(date '+%Y%m%d_%H%M%S').log"
  log_line "INFO" "日志初始化"
}

read_choice_value() {
  local prompt="$1"
  local allowed="$2"
  local default_value="${3:-}"
  local answer normalized

  while true; do
    if [[ -n "${default_value}" ]]; then
      read -r -p "${prompt} [${default_value}] " answer || true
      [[ -z "${answer//[[:space:]]/}" ]] && answer="${default_value}"
    else
      read -r -p "${prompt} " answer || true
    fi

    normalized="$(printf '%s' "${answer}" | tr '[:lower:]' '[:upper:]' | xargs)"
    IFS='/' read -r -a allowed_values <<< "${allowed}"
    for candidate in "${allowed_values[@]}"; do
      if [[ "${normalized}" == "$(printf '%s' "${candidate}" | tr '[:lower:]' '[:upper:]')" ]]; then
        printf '%s\n' "${candidate}"
        return 0
      fi
    done
    printf '%s[!] 输入无效，可选值：%s%s\n' "${COLOR_YELLOW}" "${allowed}" "${COLOR_RESET}" >&2
  done
}

read_yes_no() {
  local prompt="$1"
  local default_value="${2:-1}"
  local default_label answer normalized
  if [[ "${default_value}" == "1" ]]; then
    default_label="Y/n"
  else
    default_label="y/N"
  fi

  while true; do
    read -r -p "${prompt} (${default_label}) " answer || true
    if [[ -z "${answer//[[:space:]]/}" ]]; then
      printf '%s\n' "${default_value}"
      return 0
    fi
    normalized="$(printf '%s' "${answer}" | tr '[:lower:]' '[:upper:]' | xargs)"
    case "${normalized}" in
      Y|YES) printf '1\n'; return 0 ;;
      N|NO) printf '0\n'; return 0 ;;
      *) printf '%s[!] 请输入 Y 或 N%s\n' "${COLOR_YELLOW}" "${COLOR_RESET}" >&2 ;;
    esac
  done
}

read_text_with_default() {
  local prompt="$1"
  local default_value="${2:-}"
  local answer
  if [[ -n "${default_value}" ]]; then
    read -r -p "${prompt} [${default_value}] " answer || true
    [[ -z "${answer//[[:space:]]/}" ]] && answer="${default_value}"
  else
    read -r -p "${prompt} " answer || true
  fi
  printf '%s\n' "$(printf '%s' "${answer}" | xargs)"
}

host_python() {
  if command_exists python3; then
    printf 'python3\n'
  elif command_exists python; then
    printf 'python\n'
  else
    return 1
  fi
}

venv_python() {
  if [[ -x ".venv/bin/python" ]]; then
    printf '%s\n' "${PROJECT_ROOT}/.venv/bin/python"
  elif [[ -x ".venv/Scripts/python.exe" ]]; then
    printf '%s\n' "${PROJECT_ROOT}/.venv/Scripts/python.exe"
  elif [[ -x ".venv/Scripts/python" ]]; then
    printf '%s\n' "${PROJECT_ROOT}/.venv/Scripts/python"
  else
    return 1
  fi
}

resolve_uv_executable_path() {
  if [[ -n "${VWR_UV_PATH:-}" && -x "${VWR_UV_PATH}" ]]; then
    printf '%s\n' "${VWR_UV_PATH}"
    return 0
  fi
  if command_exists uv; then
    command -v uv
    return 0
  fi
  return 1
}

invoke_uv() {
  if [[ -z "${UV_EXECUTABLE}" ]]; then
    UV_EXECUTABLE="$(resolve_uv_executable_path || true)"
  fi
  [[ -n "${UV_EXECUTABLE}" ]] || die "未检测到 uv"
  "${UV_EXECUTABLE}" "$@"
}

is_china_like_env() {
  local locale_text="${LANG:-}${LC_ALL:-}${LC_MESSAGES:-}${TZ:-}"
  [[ "${locale_text}" == *zh* || "${locale_text}" == *Shanghai* || "${locale_text}" == *Asia/Shanghai* ]]
}

resolve_uv_default_index() {
  if [[ "${DEFAULT_INDEX_BOUND}" == "1" ]]; then
    printf '%s\n' "${DEFAULT_INDEX}"
    return 0
  fi
  if [[ -n "${UV_DEFAULT_INDEX:-}" ]]; then
    printf '%s\n' "${UV_DEFAULT_INDEX}"
    return 0
  fi
  if is_china_like_env; then
    printf '%s\n' "https://pypi.tuna.tsinghua.edu.cn/simple"
  fi
}

uv_cache_args() {
  if [[ -n "${VWR_UV_CACHE_DIR:-}" ]]; then
    printf '%s\n%s\n' "--cache-dir" "${VWR_UV_CACHE_DIR}"
  elif [[ -d ".uv-cache" ]]; then
    printf '%s\n%s\n' "--cache-dir" "${PROJECT_ROOT}/.uv-cache"
  fi
}

ensure_uv() {
  local uv_path host_py pip_index
  uv_path="$(resolve_uv_executable_path || true)"
  if [[ -n "${uv_path}" ]]; then
    UV_EXECUTABLE="${uv_path}"
    return 0
  fi

  warn "未检测到 uv，准备使用 Python pip 安装 uv"
  host_py="$(host_python || true)"
  [[ -n "${host_py}" ]] || die "无法安装 uv：未找到 uv，也未找到 python/python3"

  pip_index="$(resolve_uv_default_index || true)"
  if [[ -n "${pip_index}" ]]; then
    "${host_py}" -m pip install --upgrade uv -i "${pip_index}"
  else
    "${host_py}" -m pip install --upgrade uv
  fi

  UV_EXECUTABLE="$(resolve_uv_executable_path || true)"
  [[ -n "${UV_EXECUTABLE}" ]] || die "uv 安装失败，请手动安装：https://docs.astral.sh/uv/"
  ok "uv 安装完成：$(invoke_uv --version 2>/dev/null || true)"
}

python_version_text() {
  local python_path="$1"
  "${python_path}" --version 2>&1 | awk '{print $2}'
}

python_selector_matches() {
  local current="$1"
  local selector="$2"
  [[ "${selector}" =~ ^[0-9]+(\.[0-9]+){0,2}$ ]] || return 0
  [[ "${current}" == "${selector}" || "${current}" == "${selector}".* ]]
}

ensure_venv() {
  local python_selector="$1"
  local py current answer

  if py="$(venv_python 2>/dev/null)"; then
    current="$(python_version_text "${py}")"
    if python_selector_matches "${current}" "${python_selector}"; then
      ok "虚拟环境已存在：.venv (Python ${current})"
      return 0
    fi

    warn "检测到 .venv Python=${current}，与期望=${python_selector} 不一致，需要重建 .venv"
    if [[ "${VIRTUAL_ENV:-}" == "${PROJECT_ROOT}/.venv" ]]; then
      warn "当前终端似乎已激活 .venv，建议先执行 deactivate 后再重建"
    fi
    answer="$(read_yes_no "是否继续重建 .venv" 0)"
    [[ "${answer}" == "1" ]] || die "已取消重建 .venv"
    rm -rf ".venv"
  fi

  ensure_uv

  if [[ -d "venv" ]]; then
    warn "检测到旧虚拟环境目录 venv，将保留不处理；推荐迁移到 .venv"
  fi

  info "创建虚拟环境：.venv"
  if [[ -n "${python_selector}" ]]; then
    invoke_uv venv ".venv" --python "${python_selector}"
  else
    invoke_uv venv ".venv"
  fi

  py="$(venv_python 2>/dev/null || true)"
  [[ -n "${py}" ]] || die "虚拟环境创建失败：未找到 .venv Python"
  ok "虚拟环境创建完成：.venv (Python $(python_version_text "${py}"))"
}

setup_state_dir() {
  printf '%s\n' "${PROJECT_ROOT}/.cache/setup-state"
}

setup_state_path() {
  local dependency_set="$1"
  if [[ "${dependency_set}" == "dev" ]]; then
    printf '%s\n' "$(setup_state_dir)/dev.json"
  else
    printf '%s\n' "$(setup_state_dir)/prod.json"
  fi
}

requirements_signature() {
  local requirements_file="$1"
  local py
  py="$(venv_python 2>/dev/null || host_python)"
  "${py}" - "${PROJECT_ROOT}" "${requirements_file}" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
start = (root / sys.argv[2]).resolve()
seen = set()
parts = []

def visit(path: Path) -> None:
    path = path.resolve()
    if path in seen:
        return
    seen.add(path)
    if not path.exists():
        parts.append({"path": str(path.relative_to(root)), "missing": True})
        return
    text = path.read_text(encoding="utf-8")
    rel = str(path.relative_to(root))
    parts.append({"path": rel, "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()})
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        tokens = stripped.split()
        if tokens[0] in {"-r", "--requirement"} and len(tokens) >= 2:
            visit((path.parent / tokens[1]).resolve())

visit(start)
payload = json.dumps(parts, ensure_ascii=False, sort_keys=True)
print(hashlib.sha256(payload.encode("utf-8")).hexdigest())
PY
}

probe_packages_for_set() {
  local dependency_set="$1"
  local packages=("PyQt6" "numpy" "Pillow" "torch")
  if [[ "${dependency_set}" == "dev" ]]; then
    packages+=("pytest" "black" "mypy")
  fi
  printf '%s\n' "${packages[@]}"
}

test_python_distributions() {
  local py="$1"
  shift
  "${py}" - "$@" <<'PY'
import importlib.metadata
import sys

missing = []
for package in sys.argv[1:]:
    try:
        importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        missing.append(package)
if missing:
    print(",".join(missing))
    raise SystemExit(1)
PY
}

test_setup_dependency_state() {
  local requirements_file="$1"
  local dependency_set="$2"
  local state_path signature py current_version missing

  [[ -f "${requirements_file}" ]] || {
    DEPENDENCY_STATE_REASON="requirements_missing"
    return 1
  }

  state_path="$(setup_state_path "${dependency_set}")"
  [[ -f "${state_path}" ]] || {
    DEPENDENCY_STATE_REASON="state_missing"
    return 1
  }

  py="$(venv_python 2>/dev/null || true)"
  [[ -n "${py}" ]] || {
    DEPENDENCY_STATE_REASON="venv_missing"
    return 1
  }

  signature="$(requirements_signature "${requirements_file}")"
  current_version="$(python_version_text "${py}")"

  if ! "${py}" - "${state_path}" "${signature}" "${py}" "${current_version}" <<'PY'
import json
import sys
from pathlib import Path

path, signature, python_path, python_version = sys.argv[1:5]
data = json.loads(Path(path).read_text(encoding="utf-8"))
checks = [
    data.get("Signature") == signature,
    data.get("PythonPath") == python_path,
    data.get("PythonVersion") == python_version,
]
raise SystemExit(0 if all(checks) else 1)
PY
  then
    DEPENDENCY_STATE_REASON="signature_or_python_changed"
    return 1
  fi

  mapfile -t probe_packages < <(probe_packages_for_set "${dependency_set}")
  if ! missing="$(test_python_distributions "${py}" "${probe_packages[@]}" 2>/dev/null)"; then
    DEPENDENCY_STATE_REASON="probe_missing:${missing}"
    return 1
  fi

  DEPENDENCY_STATE_REASON="satisfied"
  return 0
}

write_setup_dependency_state() {
  local requirements_file="$1"
  local dependency_set="$2"
  local py state_path signature py_version
  py="$(venv_python)"
  state_path="$(setup_state_path "${dependency_set}")"
  signature="$(requirements_signature "${requirements_file}")"
  py_version="$(python_version_text "${py}")"
  mkdir -p "$(dirname "${state_path}")"
  "${py}" - "${state_path}" "${dependency_set}" "${requirements_file}" "${signature}" "${py}" "${py_version}" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

path, dependency_set, requirements_file, signature, python_path, python_version = sys.argv[1:7]
payload = {
    "DependencySet": dependency_set,
    "RequirementsFile": requirements_file,
    "Signature": signature,
    "PythonPath": python_path,
    "PythonVersion": python_version,
    "UpdatedAt": datetime.now(timezone.utc).isoformat(),
}
Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
PY
}

invoke_uv_pip_install() {
  local requirements_file="$1"
  local py default_index
  local args=()
  py="$(venv_python)"
  [[ -f "${requirements_file}" ]] || die "依赖文件不存在：${requirements_file}"

  ensure_uv
  args=(pip install --python "${py}" -r "${requirements_file}")
  [[ -n "${TORCH_BACKEND}" ]] && args+=(--torch-backend "${TORCH_BACKEND}")
  default_index="$(resolve_uv_default_index || true)"
  if [[ -n "${default_index}" ]]; then
    args+=(--default-index "${default_index}")
    info "默认索引：${default_index}"
  fi
  [[ -n "${INDEX_STRATEGY}" ]] && args+=(--index-strategy "${INDEX_STRATEGY}")
  while IFS= read -r cache_arg; do
    [[ -n "${cache_arg}" ]] && args+=("${cache_arg}")
  done < <(uv_cache_args)

  info "开始安装依赖（uv）：${requirements_file}"
  invoke_uv "${args[@]}"
  ok "依赖安装完成"
}

site_packages_dir() {
  local py="$1"
  "${py}" - <<'PY'
import site
paths = site.getsitepackages()
print(paths[0] if paths else site.getusersitepackages())
PY
}

install_editable_project_fallback() {
  local py sp pth_path
  py="$(venv_python)"
  sp="$(site_packages_dir "${py}")"
  mkdir -p "${sp}"
  pth_path="${sp}/video_watermark_remover_src.pth"
  printf '%s\n' "${PROJECT_ROOT}/src" > "${pth_path}"
  warn "标准 editable 安装失败，已写入 .pth 桥接：${pth_path}"
}

install_editable_project() {
  local no_deps="${1:-0}"
  local py args=()
  py="$(venv_python)"
  ensure_uv
  args=(pip install --python "${py}" -e ".")
  [[ "${no_deps}" == "1" ]] && args+=(--no-deps)
  while IFS= read -r cache_arg; do
    [[ -n "${cache_arg}" ]] && args+=("${cache_arg}")
  done < <(uv_cache_args)

  info "开始安装当前项目（editable）..."
  if invoke_uv "${args[@]}"; then
    ok "当前项目已安装为 editable"
  else
    install_editable_project_fallback
  fi
}

assert_project_importable() {
  local py
  py="$(venv_python)"
  "${py}" - <<'PY'
import app
print(getattr(app, "__file__", "app"))
PY
}

ensure_project_importable() {
  local auto_fix_setup="${1:-0}"
  if assert_project_importable >/dev/null 2>&1; then
    return 0
  fi
  if [[ "${auto_fix_setup}" == "1" ]]; then
    warn "当前环境尚未完成项目安装，AutoFix 将重新执行 setup"
    invoke_setup
    return 0
  fi
  die "当前环境尚未完成项目安装，请运行 scripts/vwr.sh 并选择[环境初始化]"
}

assert_dev_tools() {
  local py
  py="$(venv_python 2>/dev/null || true)"
  [[ -n "${py}" ]] || die "虚拟环境不存在，请运行 scripts/vwr.sh 并选择[环境初始化]，然后开启[安装开发依赖]"
  "${py}" -m pytest --version >/dev/null 2>&1 || die "未检测到 pytest（开发依赖），请重新执行环境初始化并开启[安装开发依赖]"
}

test_key_packages() {
  local fix_if_missing="${1:-0}"
  local py missing
  py="$(venv_python)"
  if ! missing="$(test_python_distributions "${py}" PyQt6 opencv-python numpy Pillow torch ultralytics 2>/dev/null)"; then
    warn "缺失关键依赖：${missing}"
    info "建议修复：重新运行 scripts/vwr.sh 并选择[环境初始化]"
    if [[ "${fix_if_missing}" == "1" ]]; then
      info "AutoFix：尝试自动安装 requirements.txt ..."
      invoke_uv_pip_install "requirements.txt"
      test_python_distributions "${py}" PyQt6 opencv-python numpy Pillow torch ultralytics >/dev/null
      ok "AutoFix：依赖已修复"
      return 0
    fi
    return 1
  fi
  ok "关键依赖检查通过"
}

lama_torchscript_download_url() {
  printf '%s\n' "https://github.com/enesmsahin/simple-lama-inpainting/releases/download/v0.1.0/big-lama.pt"
}

show_lama_torchscript_hint() {
  warn "未检测到 LaMa TorchScript 权重，深度修复可能不可用"
  info "下载地址：$(lama_torchscript_download_url)"
  info "可设置环境变量：export VWR_LAMA_MODEL_PATH=\"/path/to/big-lama.pt\""
}

show_startup_inpainting_precheck() {
  local candidates=()
  [[ -n "${VWR_LAMA_MODEL_PATH:-}" ]] && candidates+=("${VWR_LAMA_MODEL_PATH}")
  candidates+=(
    "models/big-lama.pt"
    "models/lama/big-lama.pt"
    "models/inpainting/big-lama.pt"
    "models/LaMa/big-lama.pt"
  )
  for candidate in "${candidates[@]}"; do
    if [[ -f "${candidate}" ]]; then
      ok "LaMa TorchScript 权重：${candidate}"
      return 0
    fi
  done
  show_lama_torchscript_hint
}

resolve_config_path() {
  local py config_path
  py="$(venv_python)"
  config_path="$("${py}" - <<'PY' 2>/dev/null || true
from app.config.config_manager import ConfigManager
print(ConfigManager.get_config_path())
PY
)"
  if [[ -n "${config_path}" ]]; then
    printf '%s\n' "${config_path}"
  else
    printf '%s\n' "${HOME}/.config/video-watermark-remover/config.ini"
  fi
}

save_simple_json_report() {
  local prefix="$1"
  local json_payload="$2"
  [[ "${REPORT}" == "1" ]] || return 0
  mkdir -p logs
  local path="logs/${prefix}_$(date '+%Y%m%d_%H%M%S').json"
  printf '%s\n' "${json_payload}" > "${path}"
  ok "报告已保存：${path}"
}

show_help() {
  cat <<EOF
智能视频水印去除工具 - 纯交互式 Bash 入口 (vwr.sh)
============================================================

用法：
  bash scripts/vwr.sh

菜单功能：
  1. 环境初始化：创建 .venv 并安装依赖
  2. 启动程序：环境检查后启动 main.py
  3. 代码质量检查：black / flake8 / mypy / bandit
  4. 运行测试：pytest + 可选 PowerShell E2E 脚本
  5. 覆盖率分析：pytest-cov
  6. 性能测试：生成 JSON 报告
  7. 打包构建：PyInstaller 输出 release/
  8. 清理缓存与临时文件：basic / temp / all / deep
  9. CI 模式：运行质量、单测与可选门禁

提示：
  Bash 版与 PowerShell 版保持纯交互模式，不支持旧式尾参命令。
  LaMa TorchScript 下载：$(lama_torchscript_download_url)
  环境变量：export VWR_LAMA_MODEL_PATH="/path/to/big-lama.pt"
EOF
}

show_interactive_menu_header() {
  cat <<'EOF'

============================================================
  智能视频水印去除工具 - 交互式菜单
============================================================

  1. 环境初始化
  2. 启动程序
  3. 代码质量检查
  4. 运行测试
  5. 覆盖率分析
  6. 性能测试
  7. 打包构建
  8. 清理缓存与临时文件
  9. CI 模式
  H. 查看帮助
  0. 退出

EOF
}

invoke_interactive_setup() {
  DEV="$(read_yes_no "是否安装开发依赖" 0)"
  PYTHON_SELECTOR="$(read_text_with_default "Python 版本" "3.12.10")"
  local torch_choice index_choice strategy_choice
  torch_choice="$(read_choice_value "Torch 后端：1.auto 2.cpu 3.cu121 4.cu124 5.cu126 6.cu128 7.cu130" "1/2/3/4/5/6/7" "1")"
  case "${torch_choice}" in
    1) TORCH_BACKEND="auto" ;;
    2) TORCH_BACKEND="cpu" ;;
    3) TORCH_BACKEND="cu121" ;;
    4) TORCH_BACKEND="cu124" ;;
    5) TORCH_BACKEND="cu126" ;;
    6) TORCH_BACKEND="cu128" ;;
    *) TORCH_BACKEND="cu130" ;;
  esac

  index_choice="$(read_choice_value "索引源：1.自动 2.清华镜像 3.自定义" "1/2/3" "1")"
  case "${index_choice}" in
    1) DEFAULT_INDEX=""; DEFAULT_INDEX_BOUND=0 ;;
    2) DEFAULT_INDEX="https://pypi.tuna.tsinghua.edu.cn/simple"; DEFAULT_INDEX_BOUND=1 ;;
    3) DEFAULT_INDEX="$(read_text_with_default "请输入自定义索引 URL" "")"; DEFAULT_INDEX_BOUND=1 ;;
  esac

  strategy_choice="$(read_choice_value "索引策略：1.first-index 2.unsafe-first-match 3.unsafe-best-match" "1/2/3" "1")"
  case "${strategy_choice}" in
    1) INDEX_STRATEGY="first-index" ;;
    2) INDEX_STRATEGY="unsafe-first-match" ;;
    *) INDEX_STRATEGY="unsafe-best-match" ;;
  esac
  invoke_setup
}

invoke_interactive_run() {
  AUTO_FIX="$(read_yes_no "是否自动修复常见问题" 1)"
  SKIP_CHECKS="$(read_yes_no "是否跳过启动前检查" 0)"
  invoke_run
}

invoke_interactive_quality() {
  local check_choice
  check_choice="$(read_choice_value "检查类型：1.all 2.format 3.style 4.type 5.security" "1/2/3/4/5" "1")"
  case "${check_choice}" in
    1) CHECK="all" ;;
    2) CHECK="format" ;;
    3) CHECK="style" ;;
    4) CHECK="type" ;;
    *) CHECK="security" ;;
  esac
  QUICK="$(read_yes_no "是否启用快速模式" 1)"
  FIX="$(read_yes_no "是否自动修复格式问题" 0)"
  invoke_quality
}

invoke_interactive_test() {
  local type_choice
  type_choice="$(read_choice_value "测试类型：1.unit 2.integration 3.all 4.audio 5.preferences 6.e2e 7.quality" "1/2/3/4/5/6/7" "1")"
  case "${type_choice}" in
    1) TEST_TYPE="unit" ;;
    2) TEST_TYPE="integration" ;;
    3) TEST_TYPE="all" ;;
    4) TEST_TYPE="audio" ;;
    5) TEST_TYPE="preferences" ;;
    6) TEST_TYPE="e2e" ;;
    *) TEST_TYPE="quality" ;;
  esac
  QUICK="$(read_yes_no "是否启用快速模式" 1)"
  COVERAGE="$(read_yes_no "是否附带覆盖率" 0)"
  PERFORMANCE="$(read_yes_no "是否附带性能测试" 0)"
  REPORT="$(read_yes_no "是否保存 JSON 报告" 0)"
  invoke_test
}

invoke_interactive_coverage() {
  QUICK="$(read_yes_no "是否启用快速模式" 1)"
  FAIL_ON_LOW="$(read_yes_no "是否启用最低覆盖率门禁" 0)"
  MIN_COVERAGE="$(read_text_with_default "最低覆盖率" "80")"
  OPEN_REPORT="$(read_yes_no "是否打开 HTML 报告" 0)"
  invoke_coverage
}

invoke_interactive_perf() {
  QUICK="$(read_yes_no "是否启用快速模式" 1)"
  ITERATIONS="$(read_text_with_default "迭代次数" "3")"
  GPU_PROFILE="$(read_yes_no "是否采集 GPU 信息" 1)"
  MEMORY_PROFILE="$(read_yes_no "是否采集内存信息" 1)"
  PERF_REPORT_PATH="$(read_text_with_default "报告路径（留空自动生成）" "")"
  invoke_perf
}

invoke_interactive_build() {
  QUICK="$(read_yes_no "是否启用快速模式" 1)"
  SKIP_TESTS="$(read_yes_no "是否跳过构建前测试" 0)"
  invoke_build
}

invoke_interactive_clean() {
  local scope_choice
  scope_choice="$(read_choice_value "清理级别：1.basic 2.temp 3.all 4.deep" "1/2/3/4" "3")"
  case "${scope_choice}" in
    1) CLEAN_SCOPE="basic" ;;
    2) CLEAN_SCOPE="temp" ;;
    3) CLEAN_SCOPE="all" ;;
    *) CLEAN_SCOPE="deep" ;;
  esac
  invoke_clean "${CLEAN_SCOPE}" 0
}

invoke_interactive_ci() {
  QUICK="$(read_yes_no "是否启用快速模式" 1)"
  SKIP_COVERAGE="$(read_yes_no "是否跳过覆盖率" 0)"
  SKIP_PERFORMANCE="$(read_yes_no "是否跳过性能测试" 1)"
  MIN_COVERAGE="$(read_text_with_default "最低覆盖率" "80")"
  TIMEOUT_MINUTES="$(read_text_with_default "超时分钟数" "30")"
  ARTIFACTS_DIR="$(read_text_with_default "制品目录" "logs/ci-artifacts")"
  OUTPUT_FILE="$(read_text_with_default "CI 结果文件（留空自动）" "")"
  invoke_ci
}

invoke_setup() {
  section "环境配置 (setup)"
  ensure_venv "${PYTHON_SELECTOR}"

  local requirements_file dependency_set app_path py
  if [[ "${DEV}" == "1" ]]; then
    requirements_file="requirements-dev.txt"
    dependency_set="dev"
  else
    requirements_file="requirements.txt"
    dependency_set="prod"
  fi
  info "依赖清单：${requirements_file}"

  DEPENDENCY_STATE_REASON=""
  if test_setup_dependency_state "${requirements_file}" "${dependency_set}"; then
    ok "检测到依赖已满足，跳过重复安装：${requirements_file}"
  else
    info "依赖状态未命中：${DEPENDENCY_STATE_REASON:-unknown}，执行安装：${requirements_file}"
    invoke_uv_pip_install "${requirements_file}"
    write_setup_dependency_state "requirements.txt" "prod"
    if [[ "${DEV}" == "1" ]]; then
      write_setup_dependency_state "requirements-dev.txt" "dev"
    fi
  fi

  install_editable_project 1
  app_path="$(assert_project_importable)"
  py="$(venv_python)"
  ok "Python：$("${py}" --version 2>&1)"
  ok "导入验证：${app_path}"
  ok "完成：可重新运行 bash scripts/vwr.sh，并在菜单中选择[启动程序]"
}

invoke_run() {
  initialize_log
  section "启动应用 (run)"
  ensure_uv

  if ! venv_python >/dev/null 2>&1; then
    if [[ "${AUTO_FIX}" == "1" ]]; then
      warn "虚拟环境不存在，AutoFix 将执行 setup"
      invoke_setup
    else
      die "虚拟环境不存在，请运行 bash scripts/vwr.sh 并选择[环境初始化]"
    fi
  fi

  ensure_project_importable "${AUTO_FIX}"

  local py config_ini config_dir
  py="$(venv_python)"
  if [[ "${SKIP_CHECKS}" != "1" ]]; then
    section "环境检查"
    info "Python：$("${py}" --version 2>&1)"
    test_key_packages "${AUTO_FIX}" || die "依赖检查未通过"

    if command_exists ffmpeg; then
      ok "FFmpeg：$(ffmpeg -version 2>/dev/null | head -n 1)"
    else
      warn "未检测到 FFmpeg（音频保留功能需要），请安装后确保 ffmpeg 在 PATH 中"
    fi

    config_ini="$(resolve_config_path)"
    config_dir="$(dirname "${config_ini}")"
    mkdir -p "${config_dir}"
    if [[ ! -f "${config_ini}" ]]; then
      if [[ -f "config.ini.example" && "${AUTO_FIX}" == "1" ]]; then
        cp -f "config.ini.example" "${config_ini}"
        ok "AutoFix：已从 config.ini.example 生成配置文件：${config_ini}"
      else
        warn "未找到配置文件：${config_ini}（可从 config.ini.example 复制生成）"
      fi
    else
      ok "配置文件：${config_ini}"
    fi

    section "深度修复模型体检"
    show_startup_inpainting_precheck
  else
    warn "已跳过环境检查"
  fi

  [[ -f "main.py" ]] || die "未找到 main.py：${PROJECT_ROOT}/main.py"
  section "运行 main.py"
  export PYTHONIOENCODING="utf-8"
  export PYTHONUTF8="1"
  unset PYTHONPATH || true
  info "项目路径：${PROJECT_ROOT}"
  info "日志文件：${VWR_LOG_FILE}"
  info "启动命令：${py} ${PROJECT_ROOT}/main.py"
  "${py}" "${PROJECT_ROOT}/main.py"
}

quality_targets() {
  [[ -d "src/app" ]] && printf '%s\n' "src/app"
  [[ -f "main.py" ]] && printf '%s\n' "main.py"
  [[ -d "tests" ]] && printf '%s\n' "tests"
}

invoke_quality() {
  section "代码质量检查 (quality)"
  assert_dev_tools
  ensure_project_importable 0
  local py failed=0
  py="$(venv_python)"
  mapfile -t targets < <(quality_targets)
  [[ "${#targets[@]}" -gt 0 ]] || die "未找到需要检查的目标（src/app/main.py/tests）"

  mkdir -p ".cache/black"
  export BLACK_CACHE_DIR="${BLACK_CACHE_DIR:-${PROJECT_ROOT}/.cache/black}"

  if [[ "${CHECK}" == "all" || "${CHECK}" == "format" ]]; then
    info "Black：$([[ "${FIX}" == "1" ]] && printf '格式化' || printf '检查')"
    local black_args=(--line-length 100)
    [[ "${QUICK}" == "1" ]] && black_args+=(--workers 1)
    if [[ "${FIX}" != "1" ]]; then
      black_args+=(--check)
      [[ "${QUICK}" != "1" ]] && black_args+=(--diff)
    fi
    if "${py}" -m black "${black_args[@]}" "${targets[@]}"; then ok "Black 通过"; else failed=1; err "Black 未通过"; fi
  fi

  if [[ "${CHECK}" == "all" || "${CHECK}" == "style" ]]; then
    info "Flake8：检查"
    local flake_args=()
    [[ "${QUICK}" == "1" ]] && flake_args+=(--jobs 1)
    flake_args+=("${targets[@]}")
    [[ "${QUICK}" == "1" ]] && flake_args+=(--select=E9,F63,F7,F82)
    if "${py}" -m flake8 "${flake_args[@]}"; then ok "Flake8 通过"; else failed=1; err "Flake8 未通过"; fi
  fi

  if [[ "${CHECK}" == "all" || "${CHECK}" == "type" ]]; then
    if [[ "${QUICK}" == "1" ]]; then
      warn "Quick 模式：跳过 MyPy"
    else
      info "MyPy：检查"
      if "${py}" -m mypy "src/app" "main.py"; then ok "MyPy 通过"; else failed=1; err "MyPy 未通过"; fi
    fi
  fi

  if [[ "${CHECK}" == "all" || "${CHECK}" == "security" ]]; then
    if [[ "${QUICK}" == "1" ]]; then
      warn "Quick 模式：跳过安全检查"
    else
      info "Bandit：安全检查"
      if "${py}" -m bandit -r "src/app" "main.py"; then ok "Bandit 通过"; else failed=1; err "Bandit 未通过"; fi
    fi
  fi

  [[ "${failed}" == "0" ]] || die "代码质量检查未通过"
  ok "代码质量检查完成"
}

run_powershell_script_file() {
  local script_path="$1"
  shift || true
  [[ -f "${script_path}" ]] || die "脚本不存在：${script_path}"
  if command_exists pwsh; then
    pwsh -NoProfile -ExecutionPolicy Bypass -File "${script_path}" "$@"
  elif command_exists powershell.exe; then
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "${script_path}" "$@"
  else
    warn "未检测到 pwsh/powershell.exe，跳过 PowerShell 脚本：${script_path}"
    return 0
  fi
}

invoke_pytest() {
  assert_dev_tools
  ensure_project_importable 0
  local py exit_code
  py="$(venv_python)"
  test_key_packages 0 || return 2
  mkdir -p ".cache/pytest"
  local pytest_base
  pytest_base="$(mktemp -d "${PROJECT_ROOT}/.cache/pytest/pytest.XXXXXX")"
  set +e
  "${py}" -m pytest "$@" --basetemp "${pytest_base}" --color=yes
  exit_code=$?
  set -e
  return "${exit_code}"
}

invoke_test() {
  section "测试执行 (test)"
  info "测试主分层：unit → tests/unit，integration → tests/integration，e2e → tests/e2e/ps1/*.ps1"
  local exit_code=0 code=0
  case "${TEST_TYPE}" in
    unit)
      local args=("tests/unit" "-v")
      [[ "${QUICK}" == "1" ]] && args+=("-m" "not slow")
      invoke_pytest "${args[@]}" || exit_code=$?
      ;;
    integration)
      local args=("tests/integration" "-v")
      [[ "${QUICK}" == "1" ]] && args+=("-m" "not slow")
      invoke_pytest "${args[@]}" || code=$?
      [[ "${code}" == "5" ]] && { warn "未收集到任何集成测试（pytest 退出码 5）"; code=0; }
      exit_code="${code}"
      ;;
    quality)
      invoke_quality
      ;;
    all)
      local args=("tests" "-v")
      [[ "${QUICK}" == "1" ]] && args+=("-m" "not slow")
      invoke_pytest "${args[@]}" || exit_code=$?
      if [[ "${QUICK}" != "1" ]]; then
        for ps_test in \
          "audio:tests/e2e/ps1/test_audio_processing.ps1" \
          "preferences:tests/e2e/ps1/test_user_preferences.ps1" \
          "e2e:tests/e2e/ps1/test_end_to_end.ps1"; do
          local path="${ps_test#*:}"
          if [[ -f "${path}" ]]; then
            info "运行 PowerShell 测试：${path}"
            run_powershell_script_file "${path}" || exit_code=$?
          else
            warn "未找到 PowerShell 测试脚本：${path}"
          fi
        done
      else
        warn "Quick 模式：跳过 PowerShell 端到端/音频/偏好测试"
      fi
      ;;
    audio|preferences|e2e)
      local script_path
      case "${TEST_TYPE}" in
        audio) script_path="tests/e2e/ps1/test_audio_processing.ps1" ;;
        preferences) script_path="tests/e2e/ps1/test_user_preferences.ps1" ;;
        *) script_path="tests/e2e/ps1/test_end_to_end.ps1" ;;
      esac
      info "运行 PowerShell 测试：${script_path}"
      run_powershell_script_file "${script_path}" || exit_code=$?
      ;;
    *)
      die "未知测试类型：${TEST_TYPE}"
      ;;
  esac

  if [[ "${COVERAGE}" == "1" ]]; then
    invoke_coverage || exit_code=1
  fi
  if [[ "${PERFORMANCE}" == "1" ]]; then
    invoke_perf || exit_code=1
  fi

  if [[ "${REPORT}" == "1" ]]; then
    save_simple_json_report "test_report" "{\"command\":\"test\",\"type\":\"${TEST_TYPE}\",\"exitCode\":${exit_code}}"
  fi

  [[ "${exit_code}" == "0" ]] || die "测试失败（退出码：${exit_code}）"
  ok "测试完成"
}

invoke_coverage() {
  section "覆盖率分析 (coverage)"
  assert_dev_tools
  mkdir -p logs
  rm -rf "logs/htmlcov"
  local args=(
    "tests"
    "-v"
    "--cov=app"
    "--cov-report=term-missing"
    "--cov-report=html:logs/htmlcov"
  )
  [[ "${QUICK}" == "1" ]] && args+=("-m" "not slow" "-x")
  [[ "${FAIL_ON_LOW}" == "1" ]] && args+=("--cov-fail-under=${MIN_COVERAGE}")

  local exit_code=0
  invoke_pytest "${args[@]}" || exit_code=$?
  if [[ "${exit_code}" != "0" ]]; then
    [[ "${FAIL_ON_LOW}" == "1" ]] && die "覆盖率未达标或测试失败（退出码：${exit_code}）"
    warn "覆盖率测试存在失败（退出码：${exit_code}），但已尝试生成报告"
  fi

  if [[ -f "logs/htmlcov/index.html" ]]; then
    ok "覆盖率报告：${PROJECT_ROOT}/logs/htmlcov/index.html"
    if [[ "${OPEN_REPORT}" == "1" ]]; then
      if command_exists xdg-open; then xdg-open "logs/htmlcov/index.html" >/dev/null 2>&1 || true; fi
      if command_exists open; then open "logs/htmlcov/index.html" >/dev/null 2>&1 || true; fi
    fi
  else
    warn "未找到 HTML 覆盖率报告（可能未安装 pytest-cov 或运行失败）"
  fi
}

invoke_perf() {
  section "性能基准测试 (perf)"
  local py report_path quick_flag gpu_flag mem_flag
  py="$(venv_python 2>/dev/null || true)"
  [[ -n "${py}" ]] || die "虚拟环境不存在，请运行 scripts/vwr.sh 并选择[环境初始化]"
  mkdir -p logs
  report_path="${PERF_REPORT_PATH}"
  [[ -z "${report_path}" ]] && report_path="logs/performance_report_$(date '+%Y%m%d_%H%M%S').json"
  quick_flag="$([[ "${QUICK}" == "1" ]] && printf '1' || printf '0')"
  gpu_flag="$([[ "${GPU_PROFILE}" == "1" ]] && printf '1' || printf '0')"
  mem_flag="$([[ "${MEMORY_PROFILE}" == "1" ]] && printf '1' || printf '0')"
  info "生成报告：${report_path}"
  "${py}" - "${report_path}" "${ITERATIONS}" "${quick_flag}" "${gpu_flag}" "${mem_flag}" <<'PY'
import json
import platform
import sys
import time
from pathlib import Path

def cpu_task(n: int) -> int:
    total = 0
    for i in range(n):
        total += (i * i) % 97
    return total

report_path = Path(sys.argv[1])
iterations = int(sys.argv[2])
quick = sys.argv[3] == "1"
gpu_profile = sys.argv[4] == "1"
memory_profile = sys.argv[5] == "1"
report_path.parent.mkdir(parents=True, exist_ok=True)
start = time.time()
data = {
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    "params": {"iterations": iterations, "quick": quick, "gpu_profile": gpu_profile, "memory_profile": memory_profile},
    "system": {"python": sys.version, "platform": platform.platform()},
    "benchmarks": {},
    "gpu": {},
    "memory": {},
}
try:
    import psutil
    vm = psutil.virtual_memory()
    data["system"].update({
        "cpu_count_logical": psutil.cpu_count(logical=True),
        "cpu_count_physical": psutil.cpu_count(logical=False),
        "memory_total": vm.total,
        "memory_available": vm.available,
    })
except Exception as exc:
    data["system"]["psutil_error"] = str(exc)
n = 600_000 if quick else 2_000_000
durations = []
for _ in range(max(1, iterations)):
    t0 = time.time()
    cpu_task(n)
    durations.append(time.time() - t0)
data["benchmarks"]["cpu_task"] = {
    "n": n,
    "iterations": len(durations),
    "avg_seconds": sum(durations) / len(durations),
    "min_seconds": min(durations),
    "max_seconds": max(durations),
}
if gpu_profile:
    try:
        import torch
        data["gpu"]["torch_version"] = getattr(torch, "__version__", None)
        data["gpu"]["cuda_available"] = bool(torch.cuda.is_available())
        if torch.cuda.is_available():
            data["gpu"]["device_count"] = int(torch.cuda.device_count())
            data["gpu"]["device_name"] = torch.cuda.get_device_name(0)
    except Exception as exc:
        data["gpu"]["error"] = str(exc)
if memory_profile:
    try:
        import os
        import psutil
        data["memory"]["rss"] = int(psutil.Process(os.getpid()).memory_info().rss)
    except Exception as exc:
        data["memory"]["error"] = str(exc)
data["duration_seconds"] = time.time() - start
report_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(str(report_path))
PY
  ok "性能报告已生成"
}

pyinstaller_add_data_sep() {
  case "$(uname -s 2>/dev/null || true)" in
    MINGW*|MSYS*|CYGWIN*) printf ';' ;;
    *) printf ':' ;;
  esac
}

invoke_build() {
  section "构建发布 (build)"
  local py sep icon_path
  py="$(venv_python 2>/dev/null || true)"
  [[ -n "${py}" ]] || die "虚拟环境不存在，请运行 scripts/vwr.sh 并选择[环境初始化]，然后开启[安装开发依赖]"
  ensure_project_importable 0
  ensure_uv

  info "确保 PyInstaller 已安装..."
  invoke_uv pip install --python "${py}" "PyInstaller>=5.0.0"

  if [[ "${SKIP_TESTS}" != "1" ]]; then
    info "构建前测试：$([[ "${QUICK}" == "1" ]] && printf 'unit+Quick' || printf 'unit')"
    TEST_TYPE="unit"
    invoke_test
  else
    warn "已跳过构建前测试"
  fi

  rm -rf build dist release
  find "${PROJECT_ROOT}" -maxdepth 1 -name "*.spec" -type f -delete
  sep="$(pyinstaller_add_data_sep)"
  icon_path="src/app/assets/icons/app.ico"
  local args=(
    "--onefile"
    "--windowed"
    "--name=智能水印去除工具"
    "--add-data=src/app${sep}app"
    "--add-data=models${sep}models"
    "--hidden-import=PyQt6"
    "--hidden-import=cv2"
    "--hidden-import=numpy"
    "main.py"
  )
  [[ -f "${icon_path}" ]] && args=("--icon=${icon_path}" "${args[@]}") || warn "未找到图标文件：${icon_path}"
  info "开始打包（PyInstaller）..."
  "${py}" -m PyInstaller "${args[@]}"

  mkdir -p release
  cp -R dist/. release/
  [[ -f README.md ]] && cp -f README.md release/
  [[ -f requirements.txt ]] && cp -f requirements.txt release/
  {
    printf '智能视频水印去除工具\n'
    printf '构建时间: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')"
    printf 'Python版本: %s\n' "$("${py}" --version 2>&1)"
    printf '构建环境: uv + .venv\n'
    printf '操作系统: Bash / %s\n' "$(uname -s 2>/dev/null || printf unknown)"
  } > "release/VERSION.txt"
  ok "构建完成：release/ 目录"
}

resolve_clean_targets() {
  local scope="$1"
  case "${scope}" in
    basic|all|deep)
      printf '%s\n' ".mypy_cache" ".pytest_cache" ".coverage" ".coverage.*" "logs/*.log"
      ;;
  esac
  case "${scope}" in
    temp|all|deep)
      printf '%s\n' ".cache/tmp" ".cache/pytest" ".cache/tests" ".pytest_tmp" ".tmp_*" "tmp_*" "pytest-cache-files-*" "test_output" "tests/.cache" "tests/test_data/runtime_tmp"
      ;;
  esac
  case "${scope}" in
    deep)
      printf '%s\n' ".uv-cache" ".cache/uv" ".cache/setup-state" "src/video_watermark_remover.egg-info"
      ;;
  esac
}

remove_glob_or_path() {
  local target="$1"
  local count=0
  shopt -s nullglob dotglob
  local matches=( ${target} )
  shopt -u nullglob dotglob
  if [[ "${#matches[@]}" -eq 0 ]]; then
    return 0
  fi
  for item in "${matches[@]}"; do
    rm -rf -- "${item}"
    count=$((count + 1))
  done
  printf '%s\n' "${count}"
}

invoke_clean() {
  local scope="${1:-all}"
  local skip_confirm="${2:-0}"
  section "缓存清理 (clean)"
  info "清理级别：${scope}"
  mapfile -t targets < <(resolve_clean_targets "${scope}")
  info "将清理以下内容："
  for target in "${targets[@]}"; do
    printf '  - %s\n' "${target}"
  done
  printf '  - 递归清理：__pycache__、*.pyc、*.pyo（仅 src/tests 目录）\n'
  if [[ "${skip_confirm}" != "1" ]]; then
    [[ "$(read_yes_no "是否继续清理" 0)" == "1" ]] || { warn "已取消清理"; return 0; }
  fi

  local removed=0 count
  for target in "${targets[@]}"; do
    count="$(remove_glob_or_path "${target}" || printf '0')"
    removed=$((removed + count))
  done
  count="$(remove_glob_or_path "__pycache__" || printf '0')"; removed=$((removed + count))
  count="$(remove_glob_or_path "*.pyc" || printf '0')"; removed=$((removed + count))
  count="$(remove_glob_or_path "*.pyo" || printf '0')"; removed=$((removed + count))
  if [[ -d "src" ]]; then
    while IFS= read -r -d '' path; do rm -rf -- "${path}"; removed=$((removed + 1)); done < <(find src -name "__pycache__" -type d -print0)
    while IFS= read -r -d '' path; do rm -f -- "${path}"; removed=$((removed + 1)); done < <(find src \( -name "*.pyc" -o -name "*.pyo" \) -type f -print0)
  fi
  if [[ -d "tests" ]]; then
    while IFS= read -r -d '' path; do rm -rf -- "${path}"; removed=$((removed + 1)); done < <(find tests -name "__pycache__" -type d -print0)
    while IFS= read -r -d '' path; do rm -f -- "${path}"; removed=$((removed + 1)); done < <(find tests \( -name "*.pyc" -o -name "*.pyo" \) -type f -print0)
  fi
  rmdir ".cache" >/dev/null 2>&1 || true
  ok "清理完成，共处理 ${removed} 项"
}

invoke_ci() {
  initialize_log
  section "CI 模式 (ci)"
  mkdir -p "${ARTIFACTS_DIR}"
  local deadline=$((SECONDS + TIMEOUT_MINUTES * 60))
  local overall_ok=0
  local steps_json="[]"
  local host_py
  host_py="$(host_python || true)"
  [[ -n "${host_py}" ]] || die "未找到 python/python3，无法写入 CI JSON 报告"

  add_step_result() {
    local name="$1"
    local passed="$2"
    local details="${3:-}"
    steps_json="$("${host_py}" - "${steps_json}" "${name}" "${passed}" "${details}" <<'PY'
import json
import sys
steps = json.loads(sys.argv[1])
steps.append({"name": sys.argv[2], "passed": sys.argv[3] == "1", "details": sys.argv[4]})
print(json.dumps(steps, ensure_ascii=False))
PY
)"
  }

  if (( SECONDS > deadline )); then die "CI 超时"; fi
  if ( invoke_quality ); then add_step_result "quality" 1; else overall_ok=1; add_step_result "quality" 0 "quality failed"; fi

  if (( SECONDS > deadline )); then die "CI 超时"; fi
  TEST_TYPE="unit"
  COVERAGE=0
  PERFORMANCE=0
  if ( invoke_test ); then add_step_result "unit" 1; else overall_ok=1; add_step_result "unit" 0 "unit failed"; fi

  if [[ "${SKIP_COVERAGE}" != "1" ]]; then
    if (( SECONDS > deadline )); then die "CI 超时"; fi
    local old_fail="${FAIL_ON_LOW}"
    FAIL_ON_LOW=1
    if ( invoke_coverage ); then add_step_result "coverage" 1; else overall_ok=1; add_step_result "coverage" 0 "coverage failed"; fi
    FAIL_ON_LOW="${old_fail}"
  else
    add_step_result "coverage" 1 "skipped"
  fi

  if [[ "${SKIP_PERFORMANCE}" != "1" ]]; then
    if (( SECONDS > deadline )); then die "CI 超时"; fi
    if ( invoke_perf ); then add_step_result "perf" 1; else overall_ok=1; add_step_result "perf" 0 "perf failed"; fi
  else
    add_step_result "perf" 1 "skipped"
  fi

  local out="${OUTPUT_FILE}"
  [[ -z "${out}" ]] && out="${ARTIFACTS_DIR}/ci-results.json"
  mkdir -p "$(dirname "${out}")"
  "${host_py}" - "${out}" "${overall_ok}" "${steps_json}" "${QUICK}" "${SKIP_COVERAGE}" "${SKIP_PERFORMANCE}" "${MIN_COVERAGE}" <<'PY'
import json
import sys
from datetime import datetime
out, overall, steps, quick, skip_coverage, skip_performance, min_coverage = sys.argv[1:8]
payload = {
    "timestamp": datetime.now().isoformat(),
    "success": overall == "0",
    "steps": json.loads(steps),
    "params": {
        "quick": quick == "1",
        "skipCoverage": skip_coverage == "1",
        "skipPerformance": skip_performance == "1",
        "minCoverage": int(min_coverage),
    },
}
open(out, "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False, indent=2))
PY
  ok "CI 结果已写入：${out}"
  if [[ -d logs && "${ARTIFACTS_DIR}" != logs && "${ARTIFACTS_DIR}" != logs/* ]]; then
    cp -R logs "${ARTIFACTS_DIR}/" 2>/dev/null || true
  fi
  [[ "${overall_ok}" == "0" ]] || die "CI 未通过"
}

start_interactive_menu() {
  while true; do
    show_interactive_menu_header
    local choice
    choice="$(read_choice_value "请选择操作" "1/2/3/4/5/6/7/8/9/H/0" "")"
    case "$(printf '%s' "${choice}" | tr '[:lower:]' '[:upper:]')" in
      1) invoke_interactive_setup ;;
      2) invoke_interactive_run ;;
      3) invoke_interactive_quality ;;
      4) invoke_interactive_test ;;
      5) invoke_interactive_coverage ;;
      6) invoke_interactive_perf ;;
      7) invoke_interactive_build ;;
      8) invoke_interactive_clean ;;
      9) invoke_interactive_ci ;;
      H) show_help ;;
      0) info "已退出交互式菜单"; return 0 ;;
    esac
  done
}

if [[ "$#" -gt 0 ]]; then
  warn "当前脚本是纯交互模式，请直接运行：bash scripts/vwr.sh"
  warn "不再支持旧式尾参命令：help/setup/run/test/quality/coverage/perf/build/clean/ci"
  exit 1
fi

start_interactive_menu
