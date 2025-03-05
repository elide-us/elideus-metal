@ECHO OFF
CALL npm run lint
IF ERRORLEVEL 1 (
    ECHO "npm run lint failed. Exiting."
    EXIT /b 1
)
CALL npm run type-check
IF ERRORLEVEL 1 (
    ECHO "npm run type-check failed. Exiting."
)
CALL npm run build
IF ERRORLEVEL 1 (
    ECHO "npm run build failed. Exiting."
    EXIT /b 1
)
python -m uvicorn main:app --reload
