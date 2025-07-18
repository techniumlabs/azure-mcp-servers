"""Azure DevOps MCP Server.

This module provides the main server implementation for the Azure DevOps MCP server,
including project management, repository operations, work item tracking, and pipeline management.
"""

import logfire
import os
from dotenv import load_dotenv
from loguru import logger
from mcp.server.fastmcp import FastMCP
from pathlib import Path
from tl.azure_devops_mcp_server.ado_tools import AzureDevOpsTools


def load_config() -> None:
    """Load configuration from .env file.

    Looks for .env file in the current directory and parent directories.
    """
    # Start with the current directory and move up to find .env
    current_dir = Path(os.path.dirname(os.path.abspath(__file__)))

    # Look for .env in current directory and up to 3 levels up
    for _ in range(4):
        env_file = current_dir / '.env'
        if env_file.exists():
            logger.info(f'Loading configuration from {env_file}')
            load_dotenv(dotenv_path=env_file)
            break
        current_dir = current_dir.parent
    else:
        logger.warning('No .env file found. Using environment variables if available.')


# Server constants for Azure DevOps MCP Server
SERVER_INSTRUCTIONS = """
You are an Azure DevOps expert assistant focused on helping users with:

1. Managing Azure DevOps projects and repositories
2. Working with work items, boards, and backlogs
3. Creating and managing build and release pipelines
4. Handling pull requests and code reviews
5. Setting up branch policies and security
6. Monitoring and reporting on project metrics
7. Integrating with other Azure services

Provide detailed, accurate guidance on Azure DevOps capabilities, features,
and implementation approaches. When appropriate, suggest REST API calls,
Azure CLI commands, or step-by-step instructions to help users accomplish
their development and project management tasks.

Focus on best practices for:
- Source control management with Git
- Continuous integration and deployment
- Agile project management
- Team collaboration and communication
- Security and compliance
"""

SERVER_DEPENDENCIES: list[str] = [
    'requests',
    'python-dotenv',
    'loguru',
    'logfire',
]

# Initialize MCP server
mcp: FastMCP = FastMCP(
    'tl.azure-devops-mcp-server',
    instructions=SERVER_INSTRUCTIONS,
    dependencies=SERVER_DEPENDENCIES,
)


def setup_logging() -> None:
    """Set up logging configuration."""
    # Get the Logfire write token
    logfire_write_token: str = os.environ.get('LOGFIRE_WRITE_TOKEN', '')
    if not logfire_write_token:
        logger.warning('LOGFIRE_WRITE_TOKEN not found in environment variables.')
    else:
        logger.info('LOGFIRE_WRITE_TOKEN successfully loaded.')

    logfire.configure(token=logfire_write_token)
    logger.configure(handlers=[logfire.loguru_handler()])


def register_tools() -> None:
    """Register Azure DevOps tools with the MCP server."""
    global mcp
    AzureDevOpsTools(mcp)


def main() -> None:
    """Main entry point to start the MCP server."""
    global mcp

    # Load configuration before starting the server
    load_config()

    # Configure logging
    setup_logging()

    # Register tools
    register_tools()

    logger.info('Created MCP server with Azure DevOps functions')
    mcp.run(transport='streamable-http')


if __name__ == '__main__':
    main()
