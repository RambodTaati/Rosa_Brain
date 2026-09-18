# Run ON Rosa Windows PC in elevated or normal PowerShell:
#   Set-ExecutionPolicy -Scope Process Bypass; D:\Rosa_Brain\Setup-Windows.ps1
$ErrorActionPreference = 'Stop'
$Root = 'D:\Rosa_Brain'
$Py = 'C:\Users\Rosa AI\AppData\Local\Programs\Python\Python312\python.exe'
if (-not (Test-Path $Py)) { throw "Python not found: $Py" }
Set-Location $Root
if (-not (Test-Path "$Root\.venv\Scripts\python.exe")) {
  & $Py -m venv "$Root\.venv"
}
$venvPy = "$Root\.venv\Scripts\python.exe"
& $venvPy -m pip install --upgrade pip
Write-Host 'Trying CUDA torch (cu128)...'
& $venvPy -m pip install torch --index-url https://download.pytorch.org/whl/cu128
if ($LASTEXITCODE -ne 0) {
  Write-Host 'CUDA wheel failed; installing default torch'
  & $venvPy -m pip install torch
}
& $venvPy -m pip install -r "$Root\requirements.txt"
& $venvPy -m pip install -e "$Root"
$env:ROSA_BRAIN_ROOT = $Root
& $venvPy -c "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())"
Write-Host 'Setup done. Start with: .\.venv\Scripts\python.exe -m rosa_brain'
