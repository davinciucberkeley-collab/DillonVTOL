@echo off
rem Double-click to open the VTOL engineering tools menu (tools\vtol.py). Needs Python ("py") and, for rebuilding the website, Node.js.
cd /d "%~dp0"
chcp 65001 >nul
py tools\vtol.py menu
