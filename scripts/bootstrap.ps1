Write-Host ""
Write-Host "======================================="
Write-Host "AI Engineering Bootstrap"
Write-Host "Environment Bootstrap"
Write-Host "======================================="
Write-Host ""

Write-Host "[1/6] Operating System"
systeminfo | Select-Object -First 5

Write-Host ""
Write-Host "[2/6] Python"
python --version

Write-Host ""
Write-Host "[3/6] Git"
git --version

Write-Host ""
Write-Host "[4/6] Docker"
docker --version

Write-Host ""
Write-Host "[5/6] GPU"
nvidia-smi

Write-Host ""
Write-Host "[6/6] Virtual Environment"

if ($env:VIRTUAL_ENV)
{
    Write-Host $env:VIRTUAL_ENV
}
else
{
    Write-Host "No active virtual environment."
}

Write-Host ""
Write-Host "Bootstrap inspection completed."
