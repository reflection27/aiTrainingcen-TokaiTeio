
@echo off
cd /d "g:\gpt-sovits\v2\agent\main\plugins\RealtimeSTT-master"
start cmd /k "call test_env\Scripts\activate.bat && python g:\gpt-sovits\v2\agent\main\test_realtimestt.py && pause"
