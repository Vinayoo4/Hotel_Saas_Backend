 🚀 Azure Deployment Guide for Hotel Management Backend

This guide will walk you through deploying your Hotel Management Backend to Azure App Service with automatic CI/CD using GitHub Actions.

 📋 Prerequisites

- Azure Account: Active Azure subscription
- GitHub Repository: Your code pushed to GitHub
- Azure CLI: Installed and configured (optional but recommended)

 🎯 Deployment Options

 Option 1: GitHub Actions + Azure App Service (Recommended)
- Pros: Automatic deployment, version control, easy rollbacks
- Cons: Requires GitHub repository setup
- Best for: Production applications, team development

 Option 2: Azure CLI + Azure App Service
- Pros: Direct control, quick setup
- Cons: Manual deployment process
- Best for: Development, testing, quick prototypes

---

 🚀 Option 1: GitHub Actions + Azure App Service (Recommended)

 Step 1: Create Azure Resources

 1.1 Create Resource Group
```bash
 Using Azure CLI
az group create --name hotel-management-rg --location eastus

 Or create in Azure Portal:
 Portal → Resource Groups → Create → Name: hotel-management-rg, Region: East US
```

 1.2 Create App Service Plan
```bash
 Using Azure CLI
az appservice plan create \
  --name hotel-management-plan \
  --resource-group hotel-management-rg \
  --sku B1 \
  --is-linux

 Or create in Azure Portal:
 Portal → App Service Plans → Create → 
 Name: hotel-management-plan, OS: Linux, Pricing Plan: Basic (B1)
```

 1.3 Create Web App
```bash
 Using Azure CLI
az webapp create \
  --name hotel-management-backend \
  --resource-group hotel-management-rg \
  --plan hotel-management-plan \
  --runtime "PYTHON:3.12"

 Or create in Azure Portal:
 Portal → Web Apps → Create → 
 Name: hotel-management-backend, Runtime: Python 3.12
```

 Step 2: Configure Web App Settings

 2.1 Set Environment Variables
In Azure Portal → Your Web App → Configuration → Application settings:

```bash
 Critical Settings
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-super-secret-production-key-here
JWT_SECRET_KEY=your-jwt-production-secret-here

 Database (Azure Database for PostgreSQL recommended)
DATABASE_URL=postgresql://username:password@server.postgres.database.azure.com:5432/hotel_management

 CORS (your production domain)
CORS_ALLOW_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

 Azure-specific
WEBSITES_PORT=8000
SCM_DO_BUILD_DURING_DEPLOYMENT=true
```

 2.2 Configure Startup Command
In Azure Portal → Your Web App → Configuration → General settings:

```bash
 Startup Command
chmod +x azure-startup.sh && ./azure-startup.sh
```

 Step 3: Get Publish Profile

1. Go to Azure Portal → Your Web App → Overview
2. Click "Get publish profile"
3. Download the file (it's an XML file)
4. Copy the content (you'll need this for GitHub Secrets)

 Step 4: Set Up GitHub Secrets

1. Go to your GitHub repository → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add the secret:
   - Name: `AZURE_WEBAPP_PUBLISH_PROFILE`
   - Value: Paste the entire content of the publish profile XML file

 Step 5: Push Code to Trigger Deployment

```bash
 Add all files
git add .

 Commit changes
git commit -m "🚀 Add Azure deployment configuration"

 Push to main branch (this will trigger deployment)
git push origin main
```

---

 🔧 Option 2: Azure CLI Deployment

 Step 1: Install and Configure Azure CLI

```bash
 Install Azure CLI
 Windows: Download from https://docs.microsoft.com/en-us/cli/azure/install-azure-cli-windows
 macOS: brew install azure-cli
 Linux: curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

 Login to Azure
az login

 Set subscription (if you have multiple)
az account set --subscription "your-subscription-id"
```

 Step 2: Create and Deploy

```bash
 Create resource group
az group create --name hotel-management-rg --location eastus

 Create app service plan
az appservice plan create \
  --name hotel-management-plan \
  --resource-group hotel-management-rg \
  --sku B1 \
  --is-linux

 Create web app
az webapp create \
  --name hotel-management-backend \
  --resource-group hotel-management-rg \
  --plan hotel-management-plan \
  --runtime "PYTHON:3.12"

 Configure startup command
az webapp config set \
  --name hotel-management-backend \
  --resource-group hotel-management-rg \
  --startup-file "chmod +x azure-startup.sh && ./azure-startup.sh"

 Deploy your code
az webapp deployment source config-zip \
  --resource-group hotel-management-rg \
  --name hotel-management-backend \
  --src ./deployment-package.zip
```

---

 🗄️ Database Setup (Azure Database for PostgreSQL)

 Step 1: Create PostgreSQL Server

```bash
 Using Azure CLI
az postgres flexible-server create \
  --name hotel-management-db \
  --resource-group hotel-management-rg \
  --location eastus \
  --admin-user postgres \
  --admin-password "YourStrongPassword123!" \
  --sku-name Standard_B1ms \
  --version 14

 Or create in Azure Portal:
 Portal → Azure Database for PostgreSQL flexible servers → Create
```

 Step 2: Create Database

```bash
 Create database
az postgres flexible-server db create \
  --resource-group hotel-management-rg \
  --server-name hotel-management-db \
  --database-name hotel_management

 Configure firewall (allow Azure services)
az postgres flexible-server firewall-rule create \
  --resource-group hotel-management-rg \
  --name hotel-management-db \
  --rule-name allow-azure-services \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0
```

 Step 3: Update Environment Variables

Update your web app configuration with the new database URL:

```bash
 Get connection string
az postgres flexible-server show \
  --resource-group hotel-management-rg \
  --name hotel-management-db \
  --query "connectionString"

 Update web app settings
az webapp config appsettings set \
  --resource-group hotel-management-rg \
  --name hotel-management-backend \
  --settings DATABASE_URL="postgresql://postgres:YourStrongPassword123!@hotel-management-db.postgres.database.azure.com:5432/hotel_management"
```

---

 🔒 Security Configuration

 Step 1: Enable HTTPS

```bash
 Azure App Service automatically provides HTTPS
 Your app will be available at: https://hotel-management-backend.azurewebsites.net
```

 Step 2: Configure CORS

Update your `.env` file or Azure App Settings:

```bash
CORS_ALLOW_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
CORS_ALLOW_CREDENTIALS=true
```

 Step 3: Set Production Secrets

```bash
 Generate strong secrets
SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

 Update Azure settings
az webapp config appsettings set \
  --resource-group hotel-management-rg \
  --name hotel-management-backend \
  --settings SECRET_KEY="$SECRET_KEY" JWT_SECRET_KEY="$JWT_SECRET_KEY"
```

---

 📊 Monitoring and Logging

 Step 1: Enable Application Insights

```bash
 Create Application Insights
az monitor app-insights component create \
  --app hotel-management-insights \
  --location eastus \
  --resource-group hotel-management-rg \
  --application-type web

 Get instrumentation key
az monitor app-insights component show \
  --app hotel-management-insights \
  --resource-group hotel-management-rg \
  --query "instrumentationKey" -o tsv
```

 Step 2: View Logs

```bash
 View real-time logs
az webapp log tail \
  --name hotel-management-backend \
  --resource-group hotel-management-rg

 Download logs
az webapp log download \
  --name hotel-management-backend \
  --resource-group hotel-management-rg
```

---

 🚀 Deployment Verification

 Step 1: Check Deployment Status

```bash
 Check web app status
az webapp show \
  --name hotel-management-backend \
  --resource-group hotel-management-rg \
  --query "state"

 Check deployment status
az webapp deployment list \
  --name hotel-management-backend \
  --resource-group hotel-management-rg
```

 Step 2: Test Endpoints

```bash
 Test health endpoint
curl https://hotel-management-backend.azurewebsites.net/health

 Test API docs
curl https://hotel-management-backend.azurewebsites.net/docs

 Test root endpoint
curl https://hotel-management-backend.azurewebsites.net/
```

---

 🔧 Troubleshooting

 Common Issues and Solutions

 1. "Application Error" on Azure
```bash
 Check logs
az webapp log tail --name hotel-management-backend --resource-group hotel-management-rg

 Check startup command
az webapp config show --name hotel-management-backend --resource-group hotel-management-rg --query "startupCommand"
```

 2. "Module not found" Errors
```bash
 Check requirements.txt is in root directory
 Ensure all dependencies are listed
 Check Python version compatibility
```

 3. "Port binding failed"
```bash
 Verify WEBSITES_PORT=8000 is set
 Check startup command uses correct port
 Ensure app binds to 0.0.0.0:8000
```

 4. "Database connection failed"
```bash
 Verify DATABASE_URL is correct
 Check firewall rules allow Azure services
 Ensure database server is running
```

---

 📈 Scaling and Performance

 Step 1: Scale Up App Service Plan

```bash
 Scale to Premium plan for better performance
az appservice plan update \
  --name hotel-management-plan \
  --resource-group hotel-management-rg \
  --sku P1V2
```

 Step 2: Enable Auto-scaling

```bash
 Enable auto-scaling based on CPU
az monitor autoscale create \
  --resource-group hotel-management-rg \
  --resource hotel-management-plan \
  --resource-type Microsoft.Web/serverfarms \
  --name hotel-management-autoscale \
  --min-count 1 \
  --max-count 10 \
  --count 2
```

---

 🎯 Next Steps After Deployment

1. Test all endpoints using the deployed URL
2. Set up custom domain if needed
3. Configure SSL certificates for production
4. Set up monitoring alerts for uptime
5. Implement backup strategies for database
6. Set up CI/CD pipeline for future updates

---

 🌟 Success Checklist

- [ ] Azure Resources Created: Resource group, App Service Plan, Web App
- [ ] Environment Variables Set: Production secrets, database URL, CORS
- [ ] Startup Command Configured: Points to azure-startup.sh
- [ ] GitHub Actions Working: Automatic deployment on push
- [ ] Database Connected: PostgreSQL server running and accessible
- [ ] Application Responding: Health check endpoint working
- [ ] HTTPS Enabled: Secure access to your API
- [ ] Monitoring Active: Application Insights configured
- [ ] Logs Accessible: Real-time log viewing working

---

 🎉 Congratulations!

Your Hotel Management Backend is now deployed on Azure with:
- 🌐 Production URL: https://hotel-management-backend.azurewebsites.net
- 🚀 Automatic Deployments: Every push to main branch
- 🔒 HTTPS Security: SSL certificates enabled
- 📊 Monitoring: Application Insights active
- 🗄️ Database: PostgreSQL ready for production data

Your backend is now live and ready for production use! 🚀

---

 📞 Support Resources

- Azure Documentation: https://docs.microsoft.com/en-us/azure/
- App Service Troubleshooting: https://docs.microsoft.com/en-us/azure/app-service/troubleshoot-diagnostic-logs
- GitHub Actions: https://docs.github.com/en/actions
- PostgreSQL on Azure: https://docs.microsoft.com/en-us/azure/postgresql/

Happy deploying! 🎯
