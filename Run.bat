@echo off
chcp 65001 > nul

REM batファイルのあるディレクトリに移動
cd /d "%~dp0"

echo ========================================
echo  Kirisame Betting Simulation Dashboard
echo ========================================
echo.
echo Starting Streamlit server...
echo.

REM 仮想環境をアクティベート
call venv\Scripts\activate.bat

REM Streamlitダッシュボードを起動
streamlit run src/betting_simulation/dashboard/app.py --server.port 8501

pause