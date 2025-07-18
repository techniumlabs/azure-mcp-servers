"""Azure DevOps MCP tools for interacting with Azure DevOps resources.

This module provides tools for accessing and managing Azure DevOps resources,
including projects, repositories, work items, and pipelines using the Azure DevOps REST API.
"""

import base64
import logfire
import os
import requests
from dotenv import load_dotenv
from loguru import logger
from mcp.server.fastmcp.server import Context, FastMCP
from tl.azure_devops_mcp_server.models import (
    ADOListPipelinesResponse,
    ADOListProjectsResponse,
    ADORunPipelineResponse,
)
from typing import Any, Dict, List, Optional


class AzureDevOpsTools:
    """Tools for interacting with Azure DevOps resources."""

    def __init__(self, mcp: FastMCP) -> None:
        """Initialize Azure DevOps Tools.

        Args:
            mcp: The MCP server instance
        """
        self.mcp = mcp

        load_dotenv()  # Load environment variables from .env file

        # Get configuration from environment variables
        self.organization_url: str = os.environ.get('AZURE_DEVOPS_ORG_URL', '')
        self.personal_access_token: str = os.environ.get('AZURE_DEVOPS_PAT', '')

        if not all([self.organization_url.strip(), self.personal_access_token.strip()]):
            error_message = (
                'Missing required environment variables: AZURE_DEVOPS_ORG_URL and AZURE_DEVOPS_PAT'
            )
            logger.error(error_message)
            logfire.error('Failed to initialize Azure DevOps client', error=error_message)
            raise ValueError(error_message)

        # Ensure organization URL ends with proper format
        if not self.organization_url.endswith('/'):
            self.organization_url += '/'

        # Initialize authentication headers
        try:
            # Create basic authentication header using PAT
            credentials = base64.b64encode(f':{self.personal_access_token}'.encode()).decode()
            self.headers = {
                'Authorization': f'Basic {credentials}',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            }

            logger.info(
                f'Successfully initialized Azure DevOps client for organization: {self.organization_url}'
            )
            logfire.info(
                'Azure DevOps client initialized',
                organization_url=self.organization_url,
            )
        except Exception as e:
            error_message = f'Failed to initialize Azure DevOps client: {str(e)}'
            logger.error(error_message)
            logfire.error('Azure DevOps client initialization failed', error=str(e))
            raise Exception(error_message)

        # Register tools with the MCP server
        self.mcp.tool(
            name='list_projects', description='List all projects in the Azure DevOps organization'
        )(self.list_projects)
        self.mcp.tool(
            name='list_pipelines', description='List all pipelines in an Azure DevOps project'
        )(self.list_pipelines)
        self.mcp.tool(
            name='run_pipeline', description='Run a pipeline by name in an Azure DevOps project'
        )(self.run_pipeline)

    def list_projects(
        self,
        ctx: Context,
        include_capabilities: Optional[bool] = False,
        include_history: Optional[bool] = False,
    ) -> ADOListProjectsResponse:
        """List all projects in the Azure DevOps organization.

        Args:
            ctx: The FastMCP context
            include_capabilities: Whether to include project capabilities in the response
            include_history: Whether to include project history in the response

        Returns:
            ADOListProjectsResponse containing the list of projects and their count
        """
        try:
            # Construct the API URL for listing projects
            api_url = f'{self.organization_url}_apis/projects'

            # Add query parameters if requested
            params = {'api-version': '7.1'}

            if include_capabilities:
                params['includeCapabilities'] = 'true'
            if include_history:
                params['includeHistory'] = 'true'

            # Make the API call
            response = requests.get(api_url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()

            # Parse the response
            data = response.json()
            projects_data = data.get('value', [])

            result = []
            for project in projects_data:
                # Extract project information
                project_info = {
                    'id': project.get('id', ''),
                    'name': project.get('name', ''),
                    'description': project.get('description', ''),
                    'url': project.get('url', ''),
                    'state': project.get('state', ''),
                    'revision': project.get('revision', 0),
                    'visibility': project.get('visibility', ''),
                    'last_update_time': project.get('lastUpdateTime', None),
                }

                # Add capabilities if requested and available
                if include_capabilities and project.get('capabilities'):
                    project_info['capabilities'] = project.get('capabilities', {})

                # Add default team information if available
                if project.get('defaultTeam'):
                    default_team = project.get('defaultTeam', {})
                    project_info['default_team'] = {
                        'id': default_team.get('id', ''),
                        'name': default_team.get('name', ''),
                        'url': default_team.get('url', ''),
                    }

                result.append(project_info)

            # Sort projects by name for consistent output
            result.sort(key=lambda x: x['name'].lower())

            logger.info(f'Successfully retrieved {len(result)} projects from Azure DevOps')
            logfire.info(
                'Listed Azure DevOps projects',
                count=len(result),
                organization_url=self.organization_url,
                include_capabilities=include_capabilities,
                include_history=include_history,
            )

            return ADOListProjectsResponse(
                status='success',
                message='Successfully retrieved projects from Azure DevOps',
                projects=result,
                count=len(result),
            )

        except requests.exceptions.RequestException as e:
            error_message = f'HTTP error while listing Azure DevOps projects: {str(e)}'
            logger.error(error_message)
            logfire.error('Failed to list Azure DevOps projects', error=str(e))

            return ADOListProjectsResponse(
                status='error',
                message=error_message,
                projects=[],
                count=0,
            )
        except Exception as e:
            error_message = f'Error listing Azure DevOps projects: {str(e)}'
            logger.error(error_message)
            logfire.error('Failed to list Azure DevOps projects', error=str(e))

            return ADOListProjectsResponse(
                status='error',
                message=error_message,
                projects=[],
                count=0,
            )

    def list_pipelines(
        self,
        ctx: Context,
        project_name: str,
        pipeline_type: Optional[str] = None,
    ) -> ADOListPipelinesResponse:
        """List all pipelines in an Azure DevOps project.

        Args:
            ctx: The FastMCP context
            project_name: Name of the project to list pipelines from
            pipeline_type: Optional filter by pipeline type ('build', 'release', or None for all)

        Returns:
            ADOListPipelinesResponse containing the list of pipelines and their count
        """
        try:
            # Validate project name
            if not project_name or not project_name.strip():
                raise ValueError('Project name is required')

            project_name = project_name.strip()

            # Determine which API to use based on pipeline_type
            if pipeline_type == 'build' or pipeline_type is None:
                # Get build pipelines
                build_pipelines = self._get_build_pipelines(project_name)
            else:
                build_pipelines = []

            if pipeline_type == 'release' or pipeline_type is None:
                # Get release pipelines
                release_pipelines = self._get_release_pipelines(project_name)
            else:
                release_pipelines = []

            # Combine all pipelines
            all_pipelines = build_pipelines + release_pipelines

            # Sort pipelines by name for consistent output
            all_pipelines.sort(key=lambda x: x['name'].lower())

            logger.info(
                f'Successfully retrieved {len(all_pipelines)} pipelines from project: {project_name}'
            )
            logfire.info(
                'Listed Azure DevOps pipelines',
                count=len(all_pipelines),
                project_name=project_name,
                pipeline_type=pipeline_type,
                organization_url=self.organization_url,
            )

            return ADOListPipelinesResponse(
                status='success',
                message=f'Successfully retrieved pipelines from project: {project_name}',
                pipelines=all_pipelines,
                count=len(all_pipelines),
            )

        except requests.exceptions.RequestException as e:
            error_message = f'HTTP error while listing Azure DevOps pipelines: {str(e)}'
            logger.error(error_message)
            logfire.error('Failed to list Azure DevOps pipelines', error=str(e))

            return ADOListPipelinesResponse(
                status='error',
                message=error_message,
                pipelines=[],
                count=0,
            )
        except Exception as e:
            error_message = f'Error listing Azure DevOps pipelines: {str(e)}'
            logger.error(error_message)
            logfire.error('Failed to list Azure DevOps pipelines', error=str(e))

            return ADOListPipelinesResponse(
                status='error',
                message=error_message,
                pipelines=[],
                count=0,
            )

    def _get_build_pipelines(self, project_name: str) -> List[Dict[str, Any]]:
        """Get build pipelines for a project.

        Args:
            project_name: Name of the project

        Returns:
            List of build pipeline information
        """
        try:
            # Construct the API URL for listing build pipelines
            api_url = f'{self.organization_url}{project_name}/_apis/build/definitions'

            params = {'api-version': '7.1', 'includeAllProperties': 'true'}

            # Make the API call
            response = requests.get(api_url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()

            # Parse the response
            data = response.json()
            pipelines_data = data.get('value', [])

            result = []
            for pipeline in pipelines_data:
                pipeline_info = {
                    'id': pipeline.get('id', ''),
                    'name': pipeline.get('name', ''),
                    'type': 'build',
                    'path': pipeline.get('path', ''),
                    'url': pipeline.get('url', ''),
                    'revision': pipeline.get('revision', 0),
                    'created_date': pipeline.get('createdDate', None),
                    'queue_status': pipeline.get('queueStatus', ''),
                    'quality': pipeline.get('quality', ''),
                    'author': {},
                    'repository': {},
                }

                # Add author information if available
                if pipeline.get('authoredBy'):
                    author = pipeline.get('authoredBy', {})
                    pipeline_info['author'] = {
                        'id': author.get('id', ''),
                        'display_name': author.get('displayName', ''),
                        'unique_name': author.get('uniqueName', ''),
                    }

                # Add repository information if available
                if pipeline.get('repository'):
                    repo = pipeline.get('repository', {})
                    pipeline_info['repository'] = {
                        'id': repo.get('id', ''),
                        'name': repo.get('name', ''),
                        'type': repo.get('type', ''),
                        'url': repo.get('url', ''),
                        'default_branch': repo.get('defaultBranch', ''),
                    }

                result.append(pipeline_info)

            return result

        except requests.exceptions.RequestException as e:
            logger.warning(f'Failed to get build pipelines for project {project_name}: {str(e)}')
            return []

    def _get_release_pipelines(self, project_name: str) -> List[Dict[str, Any]]:
        """Get release pipelines for a project.

        Args:
            project_name: Name of the project

        Returns:
            List of release pipeline information
        """
        try:
            # Construct the API URL for listing release pipelines
            # Note: Release Management API has a different base URL
            api_url = f'{self.organization_url}{project_name}/_apis/release/definitions'

            params = {'api-version': '7.1', 'expand': 'environments'}

            # Make the API call
            response = requests.get(api_url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()

            # Parse the response
            data = response.json()
            pipelines_data = data.get('value', [])

            result = []
            for pipeline in pipelines_data:
                pipeline_info = {
                    'id': pipeline.get('id', ''),
                    'name': pipeline.get('name', ''),
                    'type': 'release',
                    'path': pipeline.get('path', ''),
                    'url': pipeline.get('url', ''),
                    'revision': pipeline.get('revision', 0),
                    'created_date': pipeline.get('createdOn', None),
                    'modified_date': pipeline.get('modifiedOn', None),
                    'created_by': {},
                    'modified_by': {},
                    'environments': [],
                }

                # Add creator information if available
                if pipeline.get('createdBy'):
                    creator = pipeline.get('createdBy', {})
                    pipeline_info['created_by'] = {
                        'id': creator.get('id', ''),
                        'display_name': creator.get('displayName', ''),
                        'unique_name': creator.get('uniqueName', ''),
                    }

                # Add modifier information if available
                if pipeline.get('modifiedBy'):
                    modifier = pipeline.get('modifiedBy', {})
                    pipeline_info['modified_by'] = {
                        'id': modifier.get('id', ''),
                        'display_name': modifier.get('displayName', ''),
                        'unique_name': modifier.get('uniqueName', ''),
                    }

                # Add environment information if available
                if pipeline.get('environments'):
                    environments = []
                    for env in pipeline.get('environments', []):
                        env_info = {
                            'id': env.get('id', ''),
                            'name': env.get('name', ''),
                            'rank': env.get('rank', 0),
                        }
                        environments.append(env_info)
                    pipeline_info['environments'] = environments

                result.append(pipeline_info)

            return result

        except requests.exceptions.RequestException as e:
            logger.warning(f'Failed to get release pipelines for project {project_name}: {str(e)}')
            return []

    def run_pipeline(
        self,
        ctx: Context,
        project_name: str,
        pipeline_name: str,
        branch: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> ADORunPipelineResponse:
        """Run a pipeline by name in an Azure DevOps project.

        Args:
            ctx: The FastMCP context
            project_name: Name of the project containing the pipeline
            pipeline_name: Name of the pipeline to run
            branch: Optional branch to run the pipeline on (defaults to default branch)
            parameters: Optional dictionary of parameters to pass to the pipeline

        Returns:
            ADORunPipelineResponse containing information about the triggered pipeline run
        """
        try:
            # Validate required parameters
            if not project_name or not project_name.strip():
                raise ValueError('Project name is required')
            if not pipeline_name or not pipeline_name.strip():
                raise ValueError('Pipeline name is required')

            project_name = project_name.strip()
            pipeline_name = pipeline_name.strip()

            # First, find the pipeline by name
            pipeline_definition = self._find_pipeline_by_name(project_name, pipeline_name)
            if not pipeline_definition:
                raise ValueError(
                    f'Pipeline "{pipeline_name}" not found in project "{project_name}"'
                )

            pipeline_id = pipeline_definition.get('id')
            pipeline_type = pipeline_definition.get('type')

            if not pipeline_id:
                raise ValueError(f'Pipeline "{pipeline_name}" has no ID')

            if pipeline_type == 'build':
                # Run build pipeline
                run_info = self._run_build_pipeline(
                    project_name, str(pipeline_id), branch, parameters
                )
            elif pipeline_type == 'release':
                # Run release pipeline
                run_info = self._run_release_pipeline(project_name, str(pipeline_id), parameters)
            else:
                raise ValueError(f'Unknown pipeline type: {pipeline_type}')

            logger.info(
                f'Successfully triggered pipeline "{pipeline_name}" in project "{project_name}"'
            )
            logfire.info(
                'Triggered Azure DevOps pipeline',
                project_name=project_name,
                pipeline_name=pipeline_name,
                pipeline_id=pipeline_id,
                pipeline_type=pipeline_type,
                run_id=run_info.get('id'),
                organization_url=self.organization_url,
            )

            return ADORunPipelineResponse(
                status='success',
                message=f'Successfully triggered pipeline "{pipeline_name}" in project "{project_name}"',
                run_info=run_info,
            )

        except requests.exceptions.RequestException as e:
            error_message = f'HTTP error while running Azure DevOps pipeline: {str(e)}'
            logger.error(error_message)
            logfire.error('Failed to run Azure DevOps pipeline', error=str(e))

            return ADORunPipelineResponse(
                status='error',
                message=error_message,
                run_info={},
            )
        except Exception as e:
            error_message = f'Error running Azure DevOps pipeline: {str(e)}'
            logger.error(error_message)
            logfire.error('Failed to run Azure DevOps pipeline', error=str(e))

            return ADORunPipelineResponse(
                status='error',
                message=error_message,
                run_info={},
            )

    def _find_pipeline_by_name(
        self, project_name: str, pipeline_name: str
    ) -> Optional[Dict[str, Any]]:
        """Find a pipeline by name in a project.

        Args:
            project_name: Name of the project
            pipeline_name: Name of the pipeline to find

        Returns:
            Pipeline definition if found, None otherwise
        """
        try:
            # Get both build and release pipelines
            build_pipelines = self._get_build_pipelines(project_name)
            release_pipelines = self._get_release_pipelines(project_name)

            all_pipelines = build_pipelines + release_pipelines

            # Find pipeline by name (case-insensitive)
            for pipeline in all_pipelines:
                if pipeline.get('name', '').lower() == pipeline_name.lower():
                    return pipeline

            return None

        except Exception as e:
            logger.error(
                f'Error finding pipeline "{pipeline_name}" in project "{project_name}": {str(e)}'
            )
            return None

    def _run_build_pipeline(
        self,
        project_name: str,
        pipeline_id: str,
        branch: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run a build pipeline.

        Args:
            project_name: Name of the project
            pipeline_id: ID of the pipeline to run
            branch: Optional branch to run on
            parameters: Optional parameters to pass

        Returns:
            Dictionary containing run information
        """
        # Construct the API URL for running build pipeline
        api_url = f'{self.organization_url}{project_name}/_apis/build/builds'

        # Prepare the request body
        request_body: Dict[str, Any] = {'definition': {'id': pipeline_id}}

        # Add branch if specified
        if branch:
            request_body['sourceBranch'] = (
                branch if branch.startswith('refs/') else f'refs/heads/{branch}'
            )

        # Add parameters if specified
        if parameters:
            request_body['parameters'] = parameters

        params = {'api-version': '7.1'}

        # Make the API call
        response = requests.post(
            api_url, headers=self.headers, params=params, json=request_body, timeout=30
        )
        response.raise_for_status()

        # Parse the response
        run_data = response.json()

        return {
            'id': run_data.get('id'),
            'number': run_data.get('buildNumber'),
            'status': run_data.get('status'),
            'result': run_data.get('result'),
            'queue_time': run_data.get('queueTime'),
            'start_time': run_data.get('startTime'),
            'finish_time': run_data.get('finishTime'),
            'url': run_data.get('url'),
            'web_url': run_data.get('_links', {}).get('web', {}).get('href'),
            'source_branch': run_data.get('sourceBranch'),
            'source_version': run_data.get('sourceVersion'),
            'type': 'build',
            'requested_by': {
                'id': run_data.get('requestedBy', {}).get('id'),
                'display_name': run_data.get('requestedBy', {}).get('displayName'),
            }
            if run_data.get('requestedBy')
            else {},
        }

    def _run_release_pipeline(
        self,
        project_name: str,
        pipeline_id: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run a release pipeline.

        Args:
            project_name: Name of the project
            pipeline_id: ID of the pipeline to run
            parameters: Optional parameters to pass

        Returns:
            Dictionary containing run information
        """
        # Construct the API URL for running release pipeline
        api_url = f'{self.organization_url}{project_name}/_apis/release/releases'

        # Prepare the request body
        request_body: Dict[str, Any] = {
            'definitionId': pipeline_id,
            'description': 'Release triggered via MCP server',
        }

        # Add parameters if specified
        if parameters:
            request_body['variables'] = parameters

        params = {'api-version': '7.1'}

        # Make the API call
        response = requests.post(
            api_url, headers=self.headers, params=params, json=request_body, timeout=30
        )
        response.raise_for_status()

        # Parse the response
        run_data = response.json()

        return {
            'id': run_data.get('id'),
            'name': run_data.get('name'),
            'status': run_data.get('status'),
            'created_on': run_data.get('createdOn'),
            'url': run_data.get('url'),
            'web_url': run_data.get('_links', {}).get('web', {}).get('href'),
            'type': 'release',
            'created_by': {
                'id': run_data.get('createdBy', {}).get('id'),
                'display_name': run_data.get('createdBy', {}).get('displayName'),
            }
            if run_data.get('createdBy')
            else {},
            'description': run_data.get('description'),
        }
