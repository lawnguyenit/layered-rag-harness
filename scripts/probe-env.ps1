# probe-env.ps1 - read-only environment probe for layered-rag-harness.
# Run from anywhere in PowerShell (output is always anchored to the repo root):  powershell -ExecutionPolicy Bypass -File scripts\probe-env.ps1
# Writes data\private\env-report.txt (git-ignored). Does NOT print env vars, PATH, keys or user names.
# It only runs version/status commands. It installs and changes nothing.

$ErrorActionPreference = 'SilentlyContinue'
$root = Split-Path $PSScriptRoot -Parent
$out = Join-Path $root 'data\private'
New-Item -ItemType Directory -Force -Path $out | Out-Null
$file = Join-Path $out 'env-report.txt'
$lines = New-Object System.Collections.Generic.List[string]
function Add-Line($s) { $lines.Add([string]$s) }
function Section($t) { Add-Line ''; Add-Line "## $t" }
function Probe($label, [scriptblock]$cmd) {
  $r = & $cmd 2>&1 | Out-String
  $r = $r.Trim()
  if ([string]::IsNullOrWhiteSpace($r)) { $r = 'NOT FOUND / no output' }
  Add-Line "[$label] $r"
}

Add-Line "probe date: $(Get-Date -Format 'yyyy-MM-dd HH:mm')"

Section 'OS and hardware'
Probe 'os' { (Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, OSArchitecture | Format-List | Out-String) }
Probe 'cpu' { (Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors | Format-List | Out-String) }
Probe 'ram_gb' { [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1) }
Probe 'gpus' { (Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion | Format-List | Out-String) }
Probe 'nvidia-smi' { nvidia-smi --query-gpu=name,memory.total,memory.used,driver_version,power.limit --format=csv }
Probe 'disks' { (Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Used -ne $null } | ForEach-Object { "{0}: used {1} GB, free {2} GB" -f $_.Name, [math]::Round($_.Used/1GB,1), [math]::Round($_.Free/1GB,1) }) -join '; ' }
Probe 'virtualization' { (Get-CimInstance Win32_Processor).VirtualizationFirmwareEnabled }
Probe 'power_scheme' { powercfg /getactivescheme }

Section 'Containers and WSL'
Probe 'docker' { docker --version }
Probe 'docker compose' { docker compose version }
Probe 'docker daemon' { docker info --format 'server={{.ServerVersion}} os={{.OperatingSystem}} cpus={{.NCPU}} mem_bytes={{.MemTotal}}' }
Probe 'docker images' { docker images --format '{{.Repository}}:{{.Tag}} {{.Size}}' }
Probe 'wsl status' { wsl --status }
Probe 'wsl distros' { wsl -l -v }

Section 'Languages and package tools'
Probe 'python' { python --version }
Probe 'py launcher' { py -0p }
Probe 'pip' { pip --version }
Probe 'uv' { uv --version }
Probe 'node' { node --version }
Probe 'npm' { npm --version }
Probe 'pnpm' { pnpm --version }
Probe 'git' { git --version }
Probe 'psql' { psql --version }
Probe 'pg_isready' { pg_isready }
Probe 'mysql' { mysql --version }
Probe 'sqlcmd' { sqlcmd -? | Select-Object -First 2 }
Probe 'cloudflared' { cloudflared --version }

Section 'AI and GPU toolchain'
Probe 'ollama' { ollama --version }
Probe 'ollama models' { ollama list }
Probe 'nvcc (CUDA Toolkit)' { nvcc --version | Select-Object -Last 2 }
$vsw = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (Test-Path $vsw) { Probe 'vs build tools' { & $vsw -products * -latest -property displayName,installationVersion } } else { Add-Line '[vs build tools] vswhere not found (likely not installed)' }
Probe 'python torch' { python -c "import torch;print(torch.__version__, 'cuda', torch.cuda.is_available())" }
Probe 'pip AI libs' { pip list 2>$null | Select-String -Pattern '^(torch|transformers|peft|trl|bitsandbytes|unsloth|sentence-transformers|llama-cpp-python|fastapi|uvicorn|sqlalchemy|psycopg|pgvector|pydantic|mcp|anthropic|google-genai|langchain|langgraph|streamlit|playwright|pytest)\s' }

Section 'Ports in use (listening)'
Probe 'ports 5432,8000,11434,5678' { Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 5432,8000,11434,5678 } | Select-Object LocalPort, OwningProcess | Format-Table | Out-String }

Section 'Project manifests under D:\Project (names only, depth 4)'
$skip = 'node_modules|\\\.venv|\\\.git\\|__pycache__'
$names = 'package.json','requirements.txt','pyproject.toml','composer.json','pom.xml','go.mod','Cargo.toml','Dockerfile','docker-compose.yml','docker-compose.yaml'
if (Test-Path 'D:\Project') {
  Get-ChildItem 'D:\Project' -Recurse -Depth 4 -File -ErrorAction SilentlyContinue |
    Where-Object { ($names -contains $_.Name -or $_.Extension -eq '.csproj') -and $_.FullName -notmatch $skip } |
    ForEach-Object { Add-Line ($_.FullName.Replace('D:\Project\','')) }
} else { Add-Line 'D:\Project not found' }

$lines | Set-Content -Path $file -Encoding UTF8
Write-Host "Done. Report written to $file"
