@echo off
setlocal

:: ────────────────────────────────────────────────────────────
::  setup_scheduler.bat
::  Crée une tâche planifiée Windows qui exécute update.py
::  automatiquement tous les jours à 03h00.
::  Lancer EN TANT QU'ADMINISTRATEUR pour que la tâche persiste.
:: ────────────────────────────────────────────────────────────

set TASK_NAME=AssistantJuridiqueIA_AutoUpdate
set PROJECT_DIR=%~dp0
set BAT_FILE=%PROJECT_DIR%run_update.bat

echo.
echo  Assistant Juridique IA - Planificateur de mises a jour
echo  ═══════════════════════════════════════════════════════
echo.
echo  Dossier      : %PROJECT_DIR%
echo  Script       : %BAT_FILE%
echo  Nom tache    : %TASK_NAME%
echo  Frequence    : Tous les jours a 03h00
echo.

:: Supprimer l'ancienne tâche si elle existe
schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1

:: Créer la nouvelle tâche : quotidienne à 03h00, lancer même si non connecté
schtasks /Create ^
  /TN "%TASK_NAME%" ^
  /TR "\"%BAT_FILE%\"" ^
  /SC DAILY ^
  /ST 03:00 ^
  /RL HIGHEST ^
  /F ^
  /NP

if %ERRORLEVEL% EQU 0 (
    echo  [OK] Tache planifiee cree avec succes.
    echo.
    echo  La mise a jour automatique s'executera chaque nuit a 03h00.
    echo  Elle detectera les nouvelles lois et mettra a jour uniquement
    echo  les index FAISS des codes modifies.
    echo.
    echo  Pour verifier : ouvrez le Planificateur de taches Windows
    echo  et cherchez "%TASK_NAME%"
    echo.
    echo  Pour lancer manuellement un seul update :
    echo    run_update.bat
) else (
    echo  [ERREUR] Impossible de creer la tache.
    echo  Relancez ce script EN TANT QU'ADMINISTRATEUR.
    echo  (Clic droit sur setup_scheduler.bat → Executer en tant qu'administrateur)
)

echo.
pause
endlocal
