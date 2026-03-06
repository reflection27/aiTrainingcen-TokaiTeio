
# 启动主程序，使用RealtimeSTT的虚拟环境

# Change to RealtimeSTT-master directory
Set-Location "g:\gpt-sovits2gent\main\plugins\RealtimeSTT-master"

# Activate virtual environment
& ".	est_env\Scripts\Activate.ps1"

# Run main program
python "g:\gpt-sovits2gent\main\main.py"

# Keep window open
Read-Host "Press Enter to exit"
