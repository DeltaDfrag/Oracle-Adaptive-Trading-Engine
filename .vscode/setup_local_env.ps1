# Make repo root discoverable by Python and VS Code
$env:PYTHONPATH = "$PWD"
[Environment]::SetEnvironmentVariable("PYTHONPATH", "$PWD", "User")
Write-Host "PYTHONPATH set to $PWD"
.\setup_local_env.ps1

