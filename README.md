# RPData Scraper for Azure

A web application for scraping property data from RP Data, processing it, and generating Excel reports. This application is Dockerized for deployment to Azure.

## Overview

This application scrapes property information from RP Data (CoreLogic) based on user-specified locations, property types, and floor area constraints. It then:

1. Downloads raw Excel files for:
   - Recent sales
   - Properties for sale
   - Properties for rent
2. Looks up zoning information for each property via Landchecker
3. Checks if the zoning allows for specific business use (Vet or Health)
4. Merges all data into a comprehensive Excel report
5. Makes the final Excel file available for download

## Project Structure

```
rpdata_scraper/
├── Dockerfile                             # Docker container configuration
├── docker-compose.yml                     # Docker Compose for local testing
├── .dockerignore                          # Files to exclude from Docker build
├── requirements.txt                       # Python dependencies
├── setup_local.sh                         # Setup script for local development 
├── run_local.sh                           # Script to run the app locally
├── app.py                                 # Main Flask application
├── static/                                # Static assets for web UI
│   ├── css/
│   │   └── styles.css                     # CSS styles
│   └── js/
│       └── script.js                      # JavaScript for UI interaction
├── templates/                             # Flask templates
│   └── index.html                         # Main page template
├── downloads/                             # Temp storage for downloaded Excel files
├── merged_properties/                     # Output directory for merged Excel files
├── tmp/                                   # Temporary storage for job status
├── rpdata_scraper/                        # Core scraper logic
│   ├── Allowable Use in the Zone - TABLE.xlsx  # Reference for zoning checks
│   ├── chrome_utils.py                    # Chrome/Selenium utilities
│   ├── check_zoning_use.py                # Check if zoning allows business type
│   ├── clear_folders.py                   # Clear temp directories
│   ├── landchecker.py                     # Scrape zoning info from Landchecker
│   ├── main.py                            # Main orchestration logic
│   ├── merge_excel.py                     # Excel merging and processing
│   └── scraper/                           # RP Data scraper components
│       ├── rpdata_base.py                 # Base scraper functionality
│       ├── setup_rpdata_scraper.py        # Setup RP Data scraper
│       └── scrape_rpdata.py               # Execute RP Data scraping
```

## Getting Started

### Local Development

1. **Setup your environment:**

   ```bash
   # Clone the repository
   git clone <your-repo-url>
   cd rpdata_scraper
   
   # Run the setup script
   chmod +x setup_local.sh
   ./setup_local.sh
   ```

2. **Run the application:**

   ```bash
   chmod +x run_local.sh
   ./run_local.sh
   ```

3. **Access the web interface:**
   
   Open your browser and go to http://127.0.0.1:5000

### Docker Development

1. **Build and run with Docker Compose:**

   ```bash
   docker-compose up --build
   ```

2. **Access the web interface:**
   
   Open your browser and go to http://localhost:5000

## Deployment to Azure

### Prerequisites

- Azure account
- Azure CLI installed and authenticated
- Docker installed

### Deployment Steps

1. **Build your Docker image:**

   ```bash
   docker build -t rpdata-scraper:latest .
   ```

2. **Tag the image for Azure Container Registry:**

   ```bash
   # Login to Azure
   az login
   
   # Create a resource group if you don't have one
   az group create --name rpdata-scraper-rg --location eastus
   
   # Create an Azure Container Registry
   az acr create --resource-group rpdata-scraper-rg --name rpdatascraperacr --sku Basic
   
   # Login to ACR
   az acr login --name rpdatascraperacr
   
   # Tag the image
   docker tag rpdata-scraper:latest rpdatascraperacr.azurecr.io/rpdata-scraper:latest
   
   # Push the image
   docker push rpdatascraperacr.azurecr.io/rpdata-scraper:latest
   ```

3. **Create an Azure App Service:**

   ```bash
   # Create a plan (B2 is recommended for this workload)
   az appservice plan create --resource-group rpdata-scraper-rg --name rpdata-scraper-plan --is-linux --sku B2
   
   # Create the web app
   az webapp create --resource-group rpdata-scraper-rg --plan rpdata-scraper-plan --name rpdata-scraper-app --deployment-container-image-name rpdatascraperacr.azurecr.io/rpdata-scraper:latest
   ```

4. **Configure Azure File Share for Persistent Storage:**

   ```bash
   # Create a storage account
   az storage account create --resource-group rpdata-scraper-rg --name rpsdatastorage --location eastus --sku Standard_LRS
   
   # Create file shares
   az storage share create --account-name rpsdatastorage --name downloads
   az storage share create --account-name rpsdatastorage --name merged-properties
   az storage share create --account-name rpsdatastorage --name tmp
   
   # Get storage account key
   STORAGE_KEY=$(az storage account keys list --resource-group rpdata-scraper-rg --account-name rpsdatastorage --query "[0].value" -o tsv)
   
   # Configure the web app to use the file shares
   az webapp config storage-account add --resource-group rpdata-scraper-rg --name rpdata-scraper-app --custom-id downloads --storage-type AzureFiles --account-name rpsdatastorage --share-name downloads --access-key $STORAGE_KEY --mount-path /app/downloads
   
   az webapp config storage-account add --resource-group rpdata-scraper-rg --name rpdata-scraper-app --custom-id merged-properties --storage-type AzureFiles --account-name rpsdatastorage --share-name merged-properties --access-key $STORAGE_KEY --mount-path /app/merged_properties
   
   az webapp config storage-account add --resource-group rpdata-scraper-rg --name rpdata-scraper-app --custom-id tmp --storage-type AzureFiles --account-name rpsdatastorage --share-name tmp --access-key $STORAGE_KEY --mount-path /app/tmp
   ```

5. **Configure App Settings:**

   ```bash
   az webapp config appsettings set --resource-group rpdata-scraper-rg --name rpdata-scraper-app --settings RUNNING_IN_DOCKER=true WEBSITES_PORT=5000
   ```

6. **Access your deployed application:**

   Open your browser and go to https://rpdata-scraper-app.azurewebsites.net

## Configuration

The application is configured through environment variables:

- `RUNNING_IN_DOCKER`: Set to 'true' when running in a container
- `PORT`: Override the default port (5000)
- `FLASK_DEBUG`: Set to '1' to enable debug mode (not recommended in production)

## Integrating with SharePoint

To save the final Excel file to a SharePoint folder, you'll need to:

1. Register an Azure AD application with the right permissions
2. Modify the app to use Microsoft Graph API to upload files

Full SharePoint integration implementation is beyond the scope of this README, but the general approach would be:

1. Get an access token for Microsoft Graph
2. Use the token to upload the file to SharePoint
3. Delete the local copy after successful upload

## Troubleshooting

### Common Issues

1. **Selenium/Chrome errors:**
   - Check Chrome installation in the container
   - Verify the Chrome driver version is compatible with Chrome

2. **File permission issues:**
   - Ensure the app has write access to the mounted volumes

3. **No results from scraping:**
   - Check if RP Data login credentials are correct
   - Verify the search parameters are valid

### Logs

- Application logs are written to `rpdata_scraper.log`
- In the container, logs are also streamed to standard output

## License

This project is proprietary and not licensed for public use.