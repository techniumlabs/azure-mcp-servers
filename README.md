# Azure MCP Server

This is a Model Context Protocol (MCP) server for Azure Services. It allows you to interact with Azure resources using the Model Context Protocol.

## Supported Services

- Azure Devops

## Prerequisites

- Python 3.8+

## Setup

1. Clone this repository:
   ```
   git clone https://github.com/techniumlabs/azure-mcp-servers.git
   cd azure-mcp-servers
   ```

2. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Add your LOGFIRE_WRITE_TOKEN for advanced logging capabilities
   - Add your AZURE_DEVOPS_ORG_URL and AZURE_DEVOPS_PAT details for connecting to your organization

## License
MIT
