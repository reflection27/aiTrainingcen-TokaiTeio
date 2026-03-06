
# Change to RealtimeSTT-master directory
Set-Location "g:\gpt-sovits\v2\agent\main\plugins\RealtimeSTT-master"

# Activate virtual environment
& ".\test_env\Scripts\Activate.ps1"

# Run test code
python "g:\gpt-sovits\v2\agent\main\test_realtimestt.py"

# Keep window open
Read-Host "Press Enter to exit"
