@echo off
setlocal
where py >NUL 2>&1 && (py -3 setup.py) || (python setup.py)
echo.
pause
