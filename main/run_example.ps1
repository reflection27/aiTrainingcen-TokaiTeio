
# Change to RealtimeSTT-master directory
Set-Location "g:\gpt-sovits\v2\agent\main\plugins\RealtimeSTT-master"

# Activate virtual environment
& ".\test_env\Scripts\Activate.ps1"

# Install RealtimeSTT in development mode
pip install -e .

# Run example
python "g:\gpt-sovits\v2\agent\main\example_realtimestt.py"

# Keep window open
Read-Host "Press Enter to exit"
