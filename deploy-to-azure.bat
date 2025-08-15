@echo off
title Azure Deployment Helper for Hotel Management Backend
color 0B

echo.
echo ========================================
echo   Azure Deployment Helper
echo   Hotel Management Backend
echo ========================================
echo.

echo 🔍 Checking prerequisites...
echo.

:: Check if Azure CLI is installed
az --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Azure CLI is not installed
    echo.
    echo Please install Azure CLI from:
    echo   https://docs.microsoft.com/en-us/cli/azure/install-azure-cli-windows
    echo.
    pause
    exit /b 1
)
echo ✅ Azure CLI is installed

:: Check if logged in to Azure
echo 🔍 Checking Azure login status...
az account show >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ⚠️  Not logged in to Azure
    echo.
    echo Please login to Azure first:
    echo   az login
    echo.
    pause
    exit /b 1
)
echo ✅ Logged in to Azure

echo.
echo ========================================
echo   Deployment Options
echo ========================================
echo.
echo 1. Create Azure resources (Resource Group, App Service Plan, Web App)
echo 2. Deploy application to existing Azure resources
echo 3. View deployment status
echo 4. Open Azure Portal
echo 5. Exit
echo.
set /p choice="Choose an option (1-5): "

if "%choice%"=="1" goto create_resources
if "%choice%"=="2" goto deploy_app
if "%choice%"=="3" goto view_status
if "%choice%"=="4" goto open_portal
if "%choice%"=="5" goto exit
goto invalid_choice

:create_resources
echo.
echo 🚀 Creating Azure resources...
echo.
set /p rg_name="Resource Group Name (default: hotel-management-rg): "
if "%rg_name%"=="" set rg_name=hotel-management-rg

set /p location="Azure Region (default: eastus): "
if "%location%"=="" set location=eastus

set /p plan_name="App Service Plan Name (default: hotel-management-plan): "
if "%plan_name%"=="" set plan_name=hotel-management-plan

set /p webapp_name="Web App Name (default: hotel-management-backend): "
if "%webapp_name%"=="" set webapp_name=hotel-management-backend

echo.
echo Creating resources with the following configuration:
echo   Resource Group: %rg_name%
echo   Location: %location%
echo   App Service Plan: %plan_name%
echo   Web App: %webapp_name%
echo.
pause

echo 🔄 Creating resource group...
az group create --name %rg_name% --location %location%

echo 🔄 Creating app service plan...
az appservice plan create --name %plan_name% --resource-group %rg_name% --sku B1 --is-linux

echo 🔄 Creating web app...
az webapp create --name %webapp_name% --resource-group %rg_name% --plan %plan_name% --runtime "PYTHON:3.12"

echo 🔄 Configuring startup command...
az webapp config set --name %webapp_name% --resource-group %rg_name% --startup-file "chmod +x azure-startup.sh && ./azure-startup.sh"

echo.
echo ✅ Azure resources created successfully!
echo.
echo Next steps:
echo 1. Configure environment variables in Azure Portal
echo 2. Set up GitHub Actions for automatic deployment
echo 3. Push your code to trigger deployment
echo.
pause
goto menu

:deploy_app
echo.
echo 🚀 Deploying application...
echo.
set /p webapp_name="Web App Name: "
set /p rg_name="Resource Group Name: "

echo 🔄 Deploying application...
az webapp deployment source config-zip --resource-group %rg_name% --name %webapp_name% --src ./deployment-package.zip

echo.
echo ✅ Application deployed successfully!
echo.
pause
goto menu

:view_status
echo.
echo 📊 Checking deployment status...
echo.
set /p webapp_name="Web App Name: "
set /p rg_name="Resource Group Name: "

echo 🔍 Web App Status:
az webapp show --name %webapp_name% --resource-group %rg_name% --query "state" -o tsv

echo.
echo 🔍 Recent Deployments:
az webapp deployment list --name %webapp_name% --resource-group %rg_name% --query "[0:3].{Status:status,Message:message,Time:endTime}" -o table

echo.
pause
goto menu

:open_portal
echo.
echo 🌐 Opening Azure Portal...
start https://portal.azure.com
echo.
pause
goto menu

:invalid_choice
echo.
echo ❌ Invalid choice. Please select 1-5.
echo.
pause
goto menu

:menu
cls
goto start

:exit
echo.
echo 👋 Goodbye! Happy deploying!
echo.
pause
exit /b 0
