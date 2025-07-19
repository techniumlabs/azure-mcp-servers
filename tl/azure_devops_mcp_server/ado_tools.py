"""Azure DevOps MCP tools for interacting with Azure DevOps resources.

This module provides tools for accessing and managing Azure DevOps resources,
including projects, repositories, work items, and pipelines using the Azure DevOps REST API.
"""

import base64
import logfire
import os
import requests
import time
from dotenv import load_dotenv
from loguru import logger
from mcp.server.fastmcp.server import Context, FastMCP
from tl.azure_devops_mcp_server.models import (
    ADOCreateProjectResponse,
    ADOCreatePullRequestResponse,
    ADOCreateRepositoryResponse,
    ADOGetPipelineLogsResponse,
    ADOListBranchesResponse,
    ADOListPipelineRunsResponse,
    ADOListPipelinesResponse,
    ADOListProjectsResponse,
    ADOListPullRequestsResponse,
    ADOListRepositoriesResponse,
    ADORerunPipelineStageResponse,
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
        self.mcp.tool(
            name='create_project',
            description='Create a new project in the Azure DevOps organization',
        )(self.create_project)
        self.mcp.tool(
            name='list_repositories',
            description='List all repositories in an Azure DevOps project',
        )(self.list_repositories)
        self.mcp.tool(
            name='list_pull_requests_by_repo',
            description='List all pull requests in a specific repository',
        )(self.list_pull_requests_by_repo)
        self.mcp.tool(
            name='list_pull_requests_by_project',
            description='List all pull requests in a project across all repositories',
        )(self.list_pull_requests_by_project)
        self.mcp.tool(
            name='list_branches',
            description='List all branches in a repository',
        )(self.list_branches)
        self.mcp.tool(
            name='create_repository',
            description='Create a new repository in an Azure DevOps project',
        )(self.create_repository)
        self.mcp.tool(
            name='create_pull_request',
            description='Create a new pull request in an Azure DevOps repository',
        )(self.create_pull_request)
        self.mcp.tool(
            name='list_pipeline_runs',
            description='List pipeline runs for a specific pipeline in an Azure DevOps project',
        )(self.list_pipeline_runs)
        self.mcp.tool(
            name='get_pipeline_logs',
            description='Get logs for a specific pipeline run or stage in Azure DevOps',
        )(self.get_pipeline_logs)
        self.mcp.tool(
            name='rerun_pipeline_stage',
            description='Rerun a specific stage of a pipeline in Azure DevOps',
        )(self.rerun_pipeline_stage)

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

    def create_project(
        self,
        ctx: Context,
        name: str,
        description: Optional[str] = None,
        visibility: Optional[str] = 'private',
        source_control_type: Optional[str] = 'Git',
        template_type_id: Optional[str] = None,
    ) -> ADOCreateProjectResponse:
        """Create a new project in the Azure DevOps organization.

        Args:
            ctx: The FastMCP context
            name: Name of the project to create
            description: Optional description for the project
            visibility: Visibility of the project ('private' or 'public', defaults to 'private')
            source_control_type: Type of source control ('Git' or 'Tfvc', defaults to 'Git')
            template_type_id: Optional template type ID for the project

        Returns:
            ADOCreateProjectResponse containing information about the created project
        """
        try:
            # Validate required parameters
            if not name or not name.strip():
                raise ValueError('Project name is required')

            name = name.strip()

            # Validate visibility
            if visibility not in ['private', 'public']:
                raise ValueError('Visibility must be either "private" or "public"')
            # Validate source control type
            if source_control_type not in ['Git', 'Tfvc']:
                raise ValueError('Source control type must be either "Git" or "Tfvc"')

            # Construct the API URL for creating projects
            api_url = f'{self.organization_url}_apis/projects'

            # Prepare the request body
            request_body: Dict[str, Any] = {
                'name': name,
                'visibility': visibility,
                'capabilities': {
                    'versioncontrol': {'sourceControlType': source_control_type},
                    'processTemplate': {
                        'templateTypeId': template_type_id
                        or '6b724908-ef14-45cf-84f8-768b5384da45'  # Basic process template
                    },
                },
            }

            # Add description if provided
            if description and description.strip():
                request_body['description'] = description.strip()

            params = {'api-version': '7.1'}

            # Make the API call to create the project
            response = requests.post(
                api_url, headers=self.headers, params=params, json=request_body, timeout=30
            )
            response.raise_for_status()

            # Parse the response
            operation_data = response.json()

            # Project creation is an asynchronous operation
            # The response contains operation details
            operation_id = operation_data.get('id')
            operation_url = operation_data.get('url')
            operation_status = operation_data.get('status')

            project_info = {
                'operation_id': operation_id,
                'operation_url': operation_url,
                'operation_status': operation_status,
                'project_name': name,
                'description': description,
                'visibility': visibility,
                'source_control_type': source_control_type,
                'template_type_id': template_type_id or '6b724908-ef14-45cf-84f8-768b5384da45',
            }

            # If the operation completed synchronously, try to get project details
            if operation_status == 'succeeded':
                try:
                    # Wait a moment and try to get the project details
                    import time

                    time.sleep(2)
                    project_details = self._get_project_details(name)
                    if project_details:
                        project_info.update(project_details)
                except Exception as e:
                    logger.warning(f'Could not retrieve project details after creation: {str(e)}')

            logger.info(f'Successfully initiated project creation for "{name}"')
            logfire.info(
                'Created Azure DevOps project',
                project_name=name,
                operation_id=operation_id,
                operation_status=operation_status,
                visibility=visibility,
                source_control_type=source_control_type,
                organization_url=self.organization_url,
            )

            return ADOCreateProjectResponse(
                status='success',
                message=f'Successfully initiated project creation for "{name}". Operation ID: {operation_id}',
                project_info=project_info,
            )

        except requests.exceptions.RequestException as e:
            error_message = f'HTTP error while creating Azure DevOps project: {str(e)}'
            logger.error(error_message)
            logfire.error('Failed to create Azure DevOps project', error=str(e))

            return ADOCreateProjectResponse(
                status='error',
                message=error_message,
                project_info={},
            )
        except Exception as e:
            error_message = f'Error creating Azure DevOps project: {str(e)}'
            logger.error(error_message)
            logfire.error('Failed to create Azure DevOps project', error=str(e))

            return ADOCreateProjectResponse(
                status='error',
                message=error_message,
                project_info={},
            )

    def _get_project_details(self, project_name: str) -> Optional[Dict[str, Any]]:
        """Get project details by name.

        Args:
            project_name: Name of the project to retrieve

        Returns:
            Project details if found, None otherwise
        """
        try:
            # Construct the API URL for getting project details
            api_url = f'{self.organization_url}_apis/projects/{project_name}'

            params = {'api-version': '7.1', 'includeCapabilities': 'true'}

            # Make the API call
            response = requests.get(api_url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()

            # Parse the response
            project_data = response.json()

            return {
                'id': project_data.get('id'),
                'name': project_data.get('name'),
                'description': project_data.get('description'),
                'url': project_data.get('url'),
                'state': project_data.get('state'),
                'revision': project_data.get('revision'),
                'visibility': project_data.get('visibility'),
                'last_update_time': project_data.get('lastUpdateTime'),
                'capabilities': project_data.get('capabilities', {}),
            }

        except requests.exceptions.RequestException as e:
            logger.warning(f'Failed to get project details for {project_name}: {str(e)}')
            return None

    def list_repositories(
        self,
        ctx: Context,
        project_name: str,
        include_links: Optional[bool] = False,
        include_all_urls: Optional[bool] = False,
    ) -> ADOListRepositoriesResponse:
        """List all repositories in an Azure DevOps project.

        Args:
            ctx: The FastMCP context
            project_name: Name of the project to list repositories from
            include_links: Whether to include repository links in the response
            include_all_urls: Whether to include all URLs in the response

        Returns:
            ADOListRepositoriesResponse containing the list of repositories and their count
        """
        try:
            # Validate project name
            if not project_name or not project_name.strip():
                raise ValueError('Project name is required')

            project_name = project_name.strip()

            # Construct the API URL for listing repositories
            api_url = f'{self.organization_url}{project_name}/_apis/git/repositories'

            # Add query parameters
            params = {'api-version': '7.1'}

            if include_links:
                params['includeLinks'] = 'true'
            if include_all_urls:
                params['includeAllUrls'] = 'true'

            # Make the API call
            response = requests.get(api_url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()

            # Parse the response
            data = response.json()
            repositories_data = data.get('value', [])

            result = []
            for repo in repositories_data:
                repo_info = {
                    'id': repo.get('id', ''),
                    'name': repo.get('name', ''),
                    'url': repo.get('url', ''),
                    'project': {
                        'id': repo.get('project', {}).get('id', ''),
                        'name': repo.get('project', {}).get('name', ''),
                        'url': repo.get('project', {}).get('url', ''),
                        'state': repo.get('project', {}).get('state', ''),
                        'visibility': repo.get('project', {}).get('visibility', ''),
                    }
                    if repo.get('project')
                    else {},
                    'default_branch': repo.get('defaultBranch', ''),
                    'size': repo.get('size', 0),
                    'remote_url': repo.get('remoteUrl', ''),
                    'ssh_url': repo.get('sshUrl', ''),
                    'web_url': repo.get('webUrl', ''),
                    'is_disabled': repo.get('isDisabled', False),
                    'is_fork': repo.get('isFork', False),
                }

                # Add links if requested and available
                if include_links and repo.get('_links'):
                    repo_info['links'] = repo.get('_links', {})

                result.append(repo_info)

            # Sort repositories by name for consistent output
            result.sort(key=lambda x: x['name'].lower())

            logger.info(
                f'Successfully retrieved {len(result)} repositories from project: {project_name}'
            )
            logfire.info(
                'Listed Azure DevOps repositories',
                count=len(result),
                project_name=project_name,
                organization_url=self.organization_url,
            )

            return ADOListRepositoriesResponse(
                status='success',
                message=f'Successfully retrieved repositories from project: {project_name}',
                repositories=result,
                count=len(result),
            )

        except requests.exceptions.RequestException as e:
            error_message = f'HTTP error while listing Azure DevOps repositories: {str(e)}'
            logger.error(error_message)
            logfire.error('Failed to list Azure DevOps repositories', error=str(e))

            return ADOListRepositoriesResponse(
                status='error',
                message=error_message,
                repositories=[],
                count=0,
            )
        except Exception as e:
            error_message = f'Error listing Azure DevOps repositories: {str(e)}'
            logger.error(error_message)
            logfire.error('Failed to list Azure DevOps repositories', error=str(e))

            return ADOListRepositoriesResponse(
                status='error',
                message=error_message,
                repositories=[],
                count=0,
            )

    def list_pull_requests_by_repo(
        self,
        ctx: Context,
        project_name: str,
        repository_name: str,
        status: Optional[str] = 'active',
        creator_id: Optional[str] = None,
        reviewer_id: Optional[str] = None,
        source_branch: Optional[str] = None,
        target_branch: Optional[str] = None,
        top: Optional[int] = 100,
    ) -> ADOListPullRequestsResponse:
        """List all pull requests in a specific repository.

        Args:
            ctx: The FastMCP context
            project_name: Name of the project containing the repository
            repository_name: Name of the repository to list pull requests from
            status: Status filter ('active', 'abandoned', 'completed', 'all')
            creator_id: Optional filter by creator ID
            reviewer_id: Optional filter by reviewer ID
            source_branch: Optional filter by source branch
            target_branch: Optional filter by target branch
            top: Maximum number of pull requests to return (default: 100)

        Returns:
            ADOListPullRequestsResponse containing the list of pull requests and their count
        """
        try:
            # Validate required parameters
            if not project_name or not project_name.strip():
                raise ValueError('Project name is required')
            if not repository_name or not repository_name.strip():
                raise ValueError('Repository name is required')

            project_name = project_name.strip()
            repository_name = repository_name.strip()

            # Construct the API URL for listing pull requests
            api_url = f'{self.organization_url}{project_name}/_apis/git/repositories/{repository_name}/pullrequests'

            # Add query parameters
            params = {'api-version': '7.1'}

            if status and status != 'all':
                params['searchCriteria.status'] = status
            if creator_id:
                params['searchCriteria.creatorId'] = creator_id
            if reviewer_id:
                params['searchCriteria.reviewerId'] = reviewer_id
            if source_branch:
                params['searchCriteria.sourceRefName'] = (
                    source_branch
                    if source_branch.startswith('refs/')
                    else f'refs/heads/{source_branch}'
                )
            if target_branch:
                params['searchCriteria.targetRefName'] = (
                    target_branch
                    if target_branch.startswith('refs/')
                    else f'refs/heads/{target_branch}'
                )
            if top:
                params['$top'] = str(top)

            # Make the API call
            response = requests.get(api_url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()

            # Parse the response
            data = response.json()
            pull_requests_data = data.get('value', [])

            result = []
            for pr in pull_requests_data:
                pr_info = {
                    'id': pr.get('pullRequestId', ''),
                    'title': pr.get('title', ''),
                    'description': pr.get('description', ''),
                    'status': pr.get('status', ''),
                    'creation_date': pr.get('creationDate', ''),
                    'closed_date': pr.get('closedDate', ''),
                    'source_branch': pr.get('sourceRefName', ''),
                    'target_branch': pr.get('targetRefName', ''),
                    'merge_status': pr.get('mergeStatus', ''),
                    'is_draft': pr.get('isDraft', False),
                    'created_by': {
                        'id': pr.get('createdBy', {}).get('id', ''),
                        'display_name': pr.get('createdBy', {}).get('displayName', ''),
                        'unique_name': pr.get('createdBy', {}).get('uniqueName', ''),
                    }
                    if pr.get('createdBy')
                    else {},
                    'reviewers': [],
                    'repository': {
                        'id': pr.get('repository', {}).get('id', ''),
                        'name': pr.get('repository', {}).get('name', ''),
                        'url': pr.get('repository', {}).get('url', ''),
                    }
                    if pr.get('repository')
                    else {},
                    'url': pr.get('url', ''),
                    'web_url': pr.get('_links', {}).get('web', {}).get('href', '')
                    if pr.get('_links')
                    else '',
                }

                # Add reviewer information if available
                if pr.get('reviewers'):
                    reviewers = []
                    for reviewer in pr.get('reviewers', []):
                        reviewer_info = {
                            'id': reviewer.get('id', ''),
                            'display_name': reviewer.get('displayName', ''),
                            'unique_name': reviewer.get('uniqueName', ''),
                            'vote': reviewer.get('vote', 0),
                            'is_required': reviewer.get('isRequired', False),
                        }
                        reviewers.append(reviewer_info)
                    pr_info['reviewers'] = reviewers

                result.append(pr_info)

            # Sort pull requests by creation date (newest first)
            result.sort(key=lambda x: x['creation_date'], reverse=True)

            logger.info(
                f'Successfully retrieved {len(result)} pull requests from repository: {repository_name}'
            )
            logfire.info(
                'Listed Azure DevOps pull requests by repository',
                count=len(result),
                project_name=project_name,
                repository_name=repository_name,
                status=status,
                organization_url=self.organization_url,
            )

            return ADOListPullRequestsResponse(
                status='success',
                message=f'Successfully retrieved pull requests from repository: {repository_name}',
                pull_requests=result,
                count=len(result),
            )

        except requests.exceptions.RequestException as e:
            error_message = f'HTTP error while listing Azure DevOps pull requests: {str(e)}'
            logger.error(error_message)
            logfire.error('Failed to list Azure DevOps pull requests', error=str(e))

            return ADOListPullRequestsResponse(
                status='error',
                message=error_message,
                pull_requests=[],
                count=0,
            )
        except Exception as e:
            error_message = f'Error listing Azure DevOps pull requests: {str(e)}'
            logger.error(error_message)
            logfire.error('Failed to list Azure DevOps pull requests', error=str(e))

            return ADOListPullRequestsResponse(
                status='error',
                message=error_message,
                pull_requests=[],
                count=0,
            )

    def list_pull_requests_by_project(
        self,
        ctx: Context,
        project_name: str,
        status: Optional[str] = 'active',
        creator_id: Optional[str] = None,
        reviewer_id: Optional[str] = None,
        top: Optional[int] = 100,
    ) -> ADOListPullRequestsResponse:
        """List all pull requests in a project across all repositories.

        Args:
            ctx: The FastMCP context
            project_name: Name of the project to list pull requests from
            status: Status filter ('active', 'abandoned', 'completed', 'all')
            creator_id: Optional filter by creator ID
            reviewer_id: Optional filter by reviewer ID
            top: Maximum number of pull requests to return (default: 100)

        Returns:
            ADOListPullRequestsResponse containing the list of pull requests and their count
        """
        try:
            # Validate project name
            if not project_name or not project_name.strip():
                raise ValueError('Project name is required')

            project_name = project_name.strip()

            # First, get all repositories in the project
            repositories_response = self.list_repositories(ctx, project_name)
            if repositories_response.get('status') != 'success':
                return ADOListPullRequestsResponse(
                    status='error',
                    message=f'Failed to get repositories from project: {repositories_response.get("message")}',
                    pull_requests=[],
                    count=0,
                )

            repositories = repositories_response.get('repositories', [])
            all_pull_requests = []

            # Get pull requests from each repository
            for repo in repositories:
                repo_name = repo.get('name', '')
                if not repo_name:
                    continue

                try:
                    pr_response = self.list_pull_requests_by_repo(
                        ctx=ctx,
                        project_name=project_name,
                        repository_name=repo_name,
                        status=status,
                        creator_id=creator_id,
                        reviewer_id=reviewer_id,
                        top=top,
                    )

                    if pr_response.get('status') == 'success':
                        repo_pull_requests = pr_response.get('pull_requests', [])
                        all_pull_requests.extend(repo_pull_requests)
                    else:
                        logger.warning(
                            f'Failed to get pull requests from repository {repo_name}: {pr_response.get("message")}'
                        )

                except Exception as e:
                    logger.warning(
                        f'Error getting pull requests from repository {repo_name}: {str(e)}'
                    )
                    continue

            # Sort all pull requests by creation date (newest first)
            all_pull_requests.sort(key=lambda x: x['creation_date'], reverse=True)

            # Apply top limit if specified
            if top and len(all_pull_requests) > top:
                all_pull_requests = all_pull_requests[:top]

            logger.info(
                f'Successfully retrieved {len(all_pull_requests)} pull requests from project: {project_name}'
            )
            logfire.info(
                'Listed Azure DevOps pull requests by project',
                count=len(all_pull_requests),
                project_name=project_name,
                status=status,
                organization_url=self.organization_url,
            )

            return ADOListPullRequestsResponse(
                status='success',
                message=f'Successfully retrieved pull requests from project: {project_name}',
                pull_requests=all_pull_requests,
                count=len(all_pull_requests),
            )

        except Exception as e:
            error_message = f'Error listing Azure DevOps pull requests by project: {str(e)}'
            logger.error(error_message)
            logfire.error('Failed to list Azure DevOps pull requests by project', error=str(e))

            return ADOListPullRequestsResponse(
                status='error',
                message=error_message,
                pull_requests=[],
                count=0,
            )

    def list_branches(
        self,
        ctx: Context,
        project_name: str,
        repository_name: str,
        filter_contains: Optional[str] = None,
        page_size: Optional[int] = 100,
    ) -> ADOListBranchesResponse:
        """List all branches in a repository.

        Args:
            ctx: The FastMCP context
            project_name: Name of the project containing the repository
            repository_name: Name of the repository to list branches from
            filter_contains: Optional filter to only return branches containing this string
            page_size: Maximum number of branches to return (default: 100)

        Returns:
            ADOListBranchesResponse containing the list of branches and their count
        """
        try:
            # Validate required parameters
            if not project_name or not project_name.strip():
                raise ValueError('Project name is required')
            if not repository_name or not repository_name.strip():
                raise ValueError('Repository name is required')

            project_name = project_name.strip()
            repository_name = repository_name.strip()

            # Construct the API URL for listing branches
            api_url = f'{self.organization_url}{project_name}/_apis/git/repositories/{repository_name}/refs'

            # Add query parameters
            params = {
                'api-version': '7.1',
                'filter': 'heads/',  # Only get branch refs
            }

            if filter_contains:
                params['filterContains'] = filter_contains
            if page_size:
                params['$top'] = str(page_size)

            # Make the API call
            response = requests.get(api_url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()

            # Parse the response
            data = response.json()
            refs_data = data.get('value', [])

            result = []
            for ref in refs_data:
                # Extract branch name from ref name (remove 'refs/heads/' prefix)
                ref_name = ref.get('name', '')
                if ref_name.startswith('refs/heads/'):
                    branch_name = ref_name[len('refs/heads/') :]
                else:
                    branch_name = ref_name

                branch_info = {
                    'name': branch_name,
                    'object_id': ref.get('objectId', ''),
                    'url': ref.get('url', ''),
                    'is_locked': ref.get('isLocked', False),
                    'creator': {
                        'id': ref.get('creator', {}).get('id', ''),
                        'display_name': ref.get('creator', {}).get('displayName', ''),
                        'unique_name': ref.get('creator', {}).get('uniqueName', ''),
                    }
                    if ref.get('creator')
                    else {},
                }

                result.append(branch_info)

            # Sort branches by name for consistent output
            result.sort(key=lambda x: x['name'].lower())

            logger.info(
                f'Successfully retrieved {len(result)} branches from repository: {repository_name}'
            )
            logfire.info(
                'Listed Azure DevOps branches',
                count=len(result),
                project_name=project_name,
                repository_name=repository_name,
                organization_url=self.organization_url,
            )

            return ADOListBranchesResponse(
                status='success',
                message=f'Successfully retrieved branches from repository: {repository_name}',
                branches=result,
                count=len(result),
            )

        except requests.exceptions.RequestException as e:
            error_message = f'HTTP error while listing Azure DevOps branches: {str(e)}'
            logger.error(error_message)
            logfire.error('Failed to list Azure DevOps branches', error=str(e))

            return ADOListBranchesResponse(
                status='error',
                message=error_message,
                branches=[],
                count=0,
            )
        except Exception as e:
            error_message = f'Error listing Azure DevOps branches: {str(e)}'
            logger.error(error_message)
            logfire.error('Failed to list Azure DevOps branches', error=str(e))

            return ADOListBranchesResponse(
                status='error',
                message=error_message,
                branches=[],
                count=0,
            )

    def create_repository(
        self,
        ctx: Context,
        project_name: str,
        repository_name: str,
        default_branch: Optional[str] = 'main',
    ) -> ADOCreateRepositoryResponse:
        """Create a new repository in an Azure DevOps project.

        Args:
            ctx: The FastMCP context
            project_name: Name of the project to create the repository in
            repository_name: Name of the repository to create
            default_branch: Optional default branch name (defaults to 'main')

        Returns:
            ADOCreateRepositoryResponse containing information about the created repository
        """
        try:
            # Validate required parameters
            if not project_name or not project_name.strip():
                raise ValueError('Project name is required')
            if not repository_name or not repository_name.strip():
                raise ValueError('Repository name is required')

            project_name = project_name.strip()
            repository_name = repository_name.strip()

            # Construct the API URL for creating repositories
            api_url = f'{self.organization_url}{project_name}/_apis/git/repositories'

            # Prepare the request body
            request_body: Dict[str, Any] = {
                'name': repository_name,
                'project': {'name': project_name},
            }

            # Add default branch if specified
            if default_branch and default_branch.strip():
                request_body['defaultBranch'] = f'refs/heads/{default_branch.strip()}'

            params = {'api-version': '7.1'}

            # Make the API call to create the repository
            response = requests.post(
                api_url, headers=self.headers, params=params, json=request_body, timeout=30
            )
            response.raise_for_status()

            # Parse the response
            repo_data = response.json()

            repository_info = {
                'id': repo_data.get('id', ''),
                'name': repo_data.get('name', ''),
                'url': repo_data.get('url', ''),
                'project': {
                    'id': repo_data.get('project', {}).get('id', ''),
                    'name': repo_data.get('project', {}).get('name', ''),
                    'url': repo_data.get('project', {}).get('url', ''),
                    'state': repo_data.get('project', {}).get('state', ''),
                    'visibility': repo_data.get('project', {}).get('visibility', ''),
                }
                if repo_data.get('project')
                else {},
                'default_branch': repo_data.get('defaultBranch', ''),
                'size': repo_data.get('size', 0),
                'remote_url': repo_data.get('remoteUrl', ''),
                'ssh_url': repo_data.get('sshUrl', ''),
                'web_url': repo_data.get('webUrl', ''),
                'is_disabled': repo_data.get('isDisabled', False),
                'is_fork': repo_data.get('isFork', False),
            }

            logger.info(
                f'Successfully created repository "{repository_name}" in project "{project_name}"'
            )
            logfire.info(
                'Created Azure DevOps repository',
                project_name=project_name,
                repository_name=repository_name,
                repository_id=repository_info.get('id'),
                organization_url=self.organization_url,
            )

            return ADOCreateRepositoryResponse(
                status='success',
                message=f'Successfully created repository "{repository_name}" in project "{project_name}"',
                repository_info=repository_info,
            )

        except requests.exceptions.RequestException as e:
            error_message = f'HTTP error while creating Azure DevOps repository: {str(e)}'
            logger.error(error_message)
            logfire.error('Failed to create Azure DevOps repository', error=str(e))

            return ADOCreateRepositoryResponse(
                status='error',
                message=error_message,
                repository_info={},
            )
        except Exception as e:
            error_message = f'Error creating Azure DevOps repository: {str(e)}'
            logger.error(error_message)
            logfire.error('Failed to create Azure DevOps repository', error=str(e))

            return ADOCreateRepositoryResponse(
                status='error',
                message=error_message,
                repository_info={},
            )

    def create_pull_request(
        self,
        ctx: Context,
        project_name: str,
        repository_name: str,
        source_branch: str,
        target_branch: str,
        title: str,
        description: Optional[str] = None,
        reviewers: Optional[List[str]] = None,
        work_items: Optional[List[str]] = None,
        is_draft: Optional[bool] = False,
        auto_complete: Optional[bool] = False,
    ) -> ADOCreatePullRequestResponse:
        """Create a new pull request in an Azure DevOps repository.

        Args:
            ctx: The FastMCP context
            project_name: Name of the project containing the repository
            repository_name: Name of the repository to create the pull request in
            source_branch: Source branch for the pull request
            target_branch: Target branch for the pull request
            title: Title of the pull request
            description: Optional description for the pull request
            reviewers: Optional list of reviewer IDs or unique names
            work_items: Optional list of work item IDs to associate with the PR
            is_draft: Whether to create the pull request as a draft (default: False)
            auto_complete: Whether to enable auto-complete (default: False)

        Returns:
            ADOCreatePullRequestResponse containing information about the created pull request
        """
        try:
            # Validate required parameters
            if not project_name or not project_name.strip():
                raise ValueError('Project name is required')
            if not repository_name or not repository_name.strip():
                raise ValueError('Repository name is required')
            if not source_branch or not source_branch.strip():
                raise ValueError('Source branch is required')
            if not target_branch or not target_branch.strip():
                raise ValueError('Target branch is required')
            if not title or not title.strip():
                raise ValueError('Title is required')

            project_name = project_name.strip()
            repository_name = repository_name.strip()
            source_branch = source_branch.strip()
            target_branch = target_branch.strip()
            title = title.strip()

            # Ensure branches have proper ref format
            if not source_branch.startswith('refs/'):
                source_branch = f'refs/heads/{source_branch}'
            if not target_branch.startswith('refs/'):
                target_branch = f'refs/heads/{target_branch}'

            # Construct the API URL for creating pull requests
            api_url = f'{self.organization_url}{project_name}/_apis/git/repositories/{repository_name}/pullrequests'

            # Prepare the request body
            request_body: Dict[str, Any] = {
                'sourceRefName': source_branch,
                'targetRefName': target_branch,
                'title': title,
                'isDraft': is_draft if is_draft is not None else False,
            }

            # Add description if provided
            if description and description.strip():
                request_body['description'] = description.strip()

            # Add reviewers if provided
            if reviewers:
                reviewer_list = []
                for reviewer in reviewers:
                    if reviewer and reviewer.strip():
                        # Check if reviewer is an ID (GUID format) or unique name
                        reviewer = reviewer.strip()
                        reviewer_info = (
                            {'id': reviewer}
                            if len(reviewer) == 36 and '-' in reviewer
                            else {'uniqueName': reviewer}
                        )
                        reviewer_list.append(reviewer_info)

                if reviewer_list:
                    request_body['reviewers'] = reviewer_list

            # Add work items if provided
            if work_items:
                work_item_refs = []
                for work_item_id in work_items:
                    if work_item_id and str(work_item_id).strip():
                        work_item_refs.append({'id': str(work_item_id).strip()})

                if work_item_refs:
                    request_body['workItemRefs'] = work_item_refs

            params = {'api-version': '7.1'}

            # Make the API call to create the pull request
            response = requests.post(
                api_url, headers=self.headers, params=params, json=request_body, timeout=30
            )
            response.raise_for_status()

            # Parse the response
            pr_data = response.json()

            pull_request_info = {
                'id': pr_data.get('pullRequestId', ''),
                'title': pr_data.get('title', ''),
                'description': pr_data.get('description', ''),
                'status': pr_data.get('status', ''),
                'creation_date': pr_data.get('creationDate', ''),
                'source_branch': pr_data.get('sourceRefName', ''),
                'target_branch': pr_data.get('targetRefName', ''),
                'merge_status': pr_data.get('mergeStatus', ''),
                'is_draft': pr_data.get('isDraft', False),
                'created_by': {
                    'id': pr_data.get('createdBy', {}).get('id', ''),
                    'display_name': pr_data.get('createdBy', {}).get('displayName', ''),
                    'unique_name': pr_data.get('createdBy', {}).get('uniqueName', ''),
                }
                if pr_data.get('createdBy')
                else {},
                'repository': {
                    'id': pr_data.get('repository', {}).get('id', ''),
                    'name': pr_data.get('repository', {}).get('name', ''),
                    'url': pr_data.get('repository', {}).get('url', ''),
                }
                if pr_data.get('repository')
                else {},
                'url': pr_data.get('url', ''),
                'web_url': pr_data.get('_links', {}).get('web', {}).get('href', '')
                if pr_data.get('_links')
                else '',
                'reviewers': [],
                'work_items': [],
            }

            # Add reviewer information if available
            if pr_data.get('reviewers'):
                reviewers_info = []
                for reviewer in pr_data.get('reviewers', []):
                    reviewer_info = {
                        'id': reviewer.get('id', ''),
                        'display_name': reviewer.get('displayName', ''),
                        'unique_name': reviewer.get('uniqueName', ''),
                        'vote': reviewer.get('vote', 0),
                        'is_required': reviewer.get('isRequired', False),
                    }
                    reviewers_info.append(reviewer_info)
                pull_request_info['reviewers'] = reviewers_info

            # Add work item information if available
            if pr_data.get('workItemRefs'):
                work_items_info = []
                for work_item in pr_data.get('workItemRefs', []):
                    work_item_info = {
                        'id': work_item.get('id', ''),
                        'url': work_item.get('url', ''),
                    }
                    work_items_info.append(work_item_info)
                pull_request_info['work_items'] = work_items_info

            # Enable auto-complete if requested
            if auto_complete:
                try:
                    pr_id = str(pull_request_info['id'])
                    self._enable_auto_complete(project_name, repository_name, pr_id)
                    pull_request_info['auto_complete_enabled'] = True
                except Exception as e:
                    logger.warning(
                        f'Failed to enable auto-complete for PR {pull_request_info["id"]}: {str(e)}'
                    )
                    pull_request_info['auto_complete_enabled'] = False

            logger.info(
                f'Successfully created pull request "{title}" in repository "{repository_name}"'
            )
            logfire.info(
                'Created Azure DevOps pull request',
                project_name=project_name,
                repository_name=repository_name,
                pull_request_id=pull_request_info.get('id'),
                title=title,
                source_branch=source_branch,
                target_branch=target_branch,
                is_draft=is_draft,
                organization_url=self.organization_url,
            )

            return ADOCreatePullRequestResponse(
                status='success',
                message=f'Successfully created pull request "{title}" in repository "{repository_name}"',
                pull_request_info=pull_request_info,
            )

        except requests.exceptions.RequestException as e:
            error_message = f'HTTP error while creating Azure DevOps pull request: {str(e)}'
            logger.error(error_message)
            logfire.error('Failed to create Azure DevOps pull request', error=str(e))

            return ADOCreatePullRequestResponse(
                status='error',
                message=error_message,
                pull_request_info={},
            )
        except Exception as e:
            error_message = f'Error creating Azure DevOps pull request: {str(e)}'
            logger.error(error_message)
            logfire.error('Failed to create Azure DevOps pull request', error=str(e))

            return ADOCreatePullRequestResponse(
                status='error',
                message=error_message,
                pull_request_info={},
            )

    def _enable_auto_complete(
        self, project_name: str, repository_name: str, pull_request_id: str
    ) -> None:
        """Enable auto-complete for a pull request.

        Args:
            project_name: Name of the project
            repository_name: Name of the repository
            pull_request_id: ID of the pull request
        """
        try:
            # Construct the API URL for updating pull request
            api_url = f'{self.organization_url}{project_name}/_apis/git/repositories/{repository_name}/pullrequests/{pull_request_id}'

            # Prepare the request body for auto-complete
            request_body = {
                'autoCompleteSetBy': {
                    'id': 'current-user'  # This will be resolved to the current authenticated user
                },
                'completionOptions': {
                    'mergeCommitMessage': f'Merged PR {pull_request_id}',
                    'deleteSourceBranch': True,
                    'squashMerge': False,
                    'transitionWorkItems': True,
                },
            }

            params = {'api-version': '7.1'}

            # Make the API call to enable auto-complete
            response = requests.patch(
                api_url, headers=self.headers, params=params, json=request_body, timeout=30
            )
            response.raise_for_status()

            logger.info(f'Successfully enabled auto-complete for pull request {pull_request_id}')

        except Exception as e:
            logger.warning(
                f'Failed to enable auto-complete for pull request {pull_request_id}: {str(e)}'
            )
            raise

    def list_pipeline_runs(
        self,
        ctx: Context,
        project_name: str,
        pipeline_name: Optional[str] = None,
        pipeline_id: Optional[str] = None,
        status: Optional[str] = None,
        reason: Optional[str] = None,
        top: Optional[int] = 50,
        branch: Optional[str] = None,
    ) -> ADOListPipelineRunsResponse:
        """List pipeline runs for a specific pipeline in an Azure DevOps project.

        Args:
            ctx: The FastMCP context
            project_name: Name of the project containing the pipeline
            pipeline_name: Optional name of the pipeline to list runs for
            pipeline_id: Optional ID of the pipeline to list runs for (takes precedence over name)
            status: Optional filter by run status ('inProgress', 'completed', 'cancelling', 'postponed')
            reason: Optional filter by run reason ('manual', 'individualCI', 'batchedCI', etc.)
            top: Maximum number of runs to return (default: 50, max: 10000)
            branch: Optional filter by source branch

        Returns:
            ADOListPipelineRunsResponse containing the list of pipeline runs and their count
        """
        try:
            # Validate required parameters
            if not project_name or not project_name.strip():
                raise ValueError('Project name is required')

            project_name = project_name.strip()

            # Get pipeline ID if pipeline name was provided
            if pipeline_name and not pipeline_id:
                pipeline_definition = self._find_pipeline_by_name(
                    project_name, pipeline_name.strip()
                )
                if not pipeline_definition:
                    raise ValueError(
                        f'Pipeline "{pipeline_name}" not found in project "{project_name}"'
                    )
                pipeline_id = str(pipeline_definition.get('id'))
                pipeline_type = pipeline_definition.get('type')
            elif pipeline_id:
                # Try to determine pipeline type by attempting to get it as a build pipeline first
                pipeline_type = 'build'  # Default assumption
            else:
                # List all pipeline runs if no specific pipeline is specified
                pipeline_id = None
                pipeline_type = 'build'  # Start with build pipelines

            if pipeline_type == 'build' or not pipeline_id:
                # Get build pipeline runs
                build_runs = self._get_build_pipeline_runs(
                    project_name, pipeline_id, status, reason, top, branch
                )
            else:
                build_runs = []

            if pipeline_type == 'release' or not pipeline_id:
                # Get release pipeline runs
                release_runs = self._get_release_pipeline_runs(
                    project_name, pipeline_id, status, top
                )
            else:
                release_runs = []

            # Combine all runs
            all_runs = build_runs + release_runs

            # Sort runs by start time (newest first)
            all_runs.sort(
                key=lambda x: x.get('start_time') or x.get('queue_time') or '1900-01-01',
                reverse=True,
            )

            # Apply top limit if we got results from multiple sources
            if top and len(all_runs) > top:
                all_runs = all_runs[:top]

            logger.info(
                f'Successfully retrieved {len(all_runs)} pipeline runs from project: {project_name}'
            )
            logfire.info(
                'Listed Azure DevOps pipeline runs',
                count=len(all_runs),
                project_name=project_name,
                pipeline_name=pipeline_name,
                pipeline_id=pipeline_id,
                status=status,
                organization_url=self.organization_url,
            )

            return ADOListPipelineRunsResponse(
                status='success',
                message=f'Successfully retrieved pipeline runs from project: {project_name}',
                runs=all_runs,
                count=len(all_runs),
            )

        except requests.exceptions.RequestException as e:
            error_message = f'HTTP error while listing Azure DevOps pipeline runs: {str(e)}'
            logger.error(error_message)
            logfire.error('Failed to list Azure DevOps pipeline runs', error=str(e))

            return ADOListPipelineRunsResponse(
                status='error',
                message=error_message,
                runs=[],
                count=0,
            )
        except Exception as e:
            error_message = f'Error listing Azure DevOps pipeline runs: {str(e)}'
            logger.error(error_message)
            logfire.error('Failed to list Azure DevOps pipeline runs', error=str(e))

            return ADOListPipelineRunsResponse(
                status='error',
                message=error_message,
                runs=[],
                count=0,
            )

    def _get_build_pipeline_runs(
        self,
        project_name: str,
        pipeline_id: Optional[str] = None,
        status: Optional[str] = None,
        reason: Optional[str] = None,
        top: Optional[int] = 50,
        branch: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get build pipeline runs for a project.

        Args:
            project_name: Name of the project
            pipeline_id: Optional ID of a specific pipeline
            status: Optional status filter
            reason: Optional reason filter
            top: Maximum number of runs to return
            branch: Optional branch filter

        Returns:
            List of build pipeline run information
        """
        try:
            # Construct the API URL for listing build runs
            api_url = f'{self.organization_url}{project_name}/_apis/build/builds'

            params = {'api-version': '7.1'}

            if pipeline_id:
                params['definitions'] = pipeline_id
            if status:
                params['statusFilter'] = status
            if reason:
                params['reasonFilter'] = reason
            if top:
                params['$top'] = str(min(top, 10000))  # API limit
            if branch:
                branch_ref = branch if branch.startswith('refs/') else f'refs/heads/{branch}'
                params['branchName'] = branch_ref

            # Make the API call
            response = requests.get(api_url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()

            # Parse the response
            data = response.json()
            builds_data = data.get('value', [])

            result = []
            for build in builds_data:
                run_info = {
                    'id': build.get('id'),
                    'number': build.get('buildNumber'),
                    'type': 'build',
                    'status': build.get('status'),
                    'result': build.get('result'),
                    'queue_time': build.get('queueTime'),
                    'start_time': build.get('startTime'),
                    'finish_time': build.get('finishTime'),
                    'source_branch': build.get('sourceBranch'),
                    'source_version': build.get('sourceVersion'),
                    'reason': build.get('reason'),
                    'url': build.get('url'),
                    'web_url': build.get('_links', {}).get('web', {}).get('href'),
                    'pipeline': {
                        'id': build.get('definition', {}).get('id'),
                        'name': build.get('definition', {}).get('name'),
                        'type': build.get('definition', {}).get('type'),
                        'url': build.get('definition', {}).get('url'),
                    }
                    if build.get('definition')
                    else {},
                    'requested_by': {
                        'id': build.get('requestedBy', {}).get('id'),
                        'display_name': build.get('requestedBy', {}).get('displayName'),
                        'unique_name': build.get('requestedBy', {}).get('uniqueName'),
                    }
                    if build.get('requestedBy')
                    else {},
                    'requested_for': {
                        'id': build.get('requestedFor', {}).get('id'),
                        'display_name': build.get('requestedFor', {}).get('displayName'),
                        'unique_name': build.get('requestedFor', {}).get('uniqueName'),
                    }
                    if build.get('requestedFor')
                    else {},
                }

                result.append(run_info)

            return result

        except requests.exceptions.RequestException as e:
            logger.warning(
                f'Failed to get build pipeline runs for project {project_name}: {str(e)}'
            )
            return []

    def _get_release_pipeline_runs(
        self,
        project_name: str,
        pipeline_id: Optional[str] = None,
        status: Optional[str] = None,
        top: Optional[int] = 50,
    ) -> List[Dict[str, Any]]:
        """Get release pipeline runs for a project.

        Args:
            project_name: Name of the project
            pipeline_id: Optional ID of a specific pipeline
            status: Optional status filter
            top: Maximum number of runs to return

        Returns:
            List of release pipeline run information
        """
        try:
            # Construct the API URL for listing releases
            api_url = f'{self.organization_url}{project_name}/_apis/release/releases'

            params = {'api-version': '7.1'}

            if pipeline_id:
                params['definitionId'] = pipeline_id
            if status:
                params['statusFilter'] = status
            if top:
                params['$top'] = str(min(top, 10000))  # API limit

            # Make the API call
            response = requests.get(api_url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()

            # Parse the response
            data = response.json()
            releases_data = data.get('value', [])

            result = []
            for release in releases_data:
                run_info = {
                    'id': release.get('id'),
                    'name': release.get('name'),
                    'type': 'release',
                    'status': release.get('status'),
                    'reason': release.get('reason'),
                    'created_on': release.get('createdOn'),
                    'modified_on': release.get('modifiedOn'),
                    'url': release.get('url'),
                    'web_url': release.get('_links', {}).get('web', {}).get('href'),
                    'pipeline': {
                        'id': release.get('releaseDefinition', {}).get('id'),
                        'name': release.get('releaseDefinition', {}).get('name'),
                        'url': release.get('releaseDefinition', {}).get('url'),
                    }
                    if release.get('releaseDefinition')
                    else {},
                    'created_by': {
                        'id': release.get('createdBy', {}).get('id'),
                        'display_name': release.get('createdBy', {}).get('displayName'),
                        'unique_name': release.get('createdBy', {}).get('uniqueName'),
                    }
                    if release.get('createdBy')
                    else {},
                    'modified_by': {
                        'id': release.get('modifiedBy', {}).get('id'),
                        'display_name': release.get('modifiedBy', {}).get('displayName'),
                        'unique_name': release.get('modifiedBy', {}).get('uniqueName'),
                    }
                    if release.get('modifiedBy')
                    else {},
                    'environments': [
                        {
                            'id': env.get('id'),
                            'name': env.get('name'),
                            'status': env.get('status'),
                            'rank': env.get('rank'),
                        }
                        for env in release.get('environments', [])
                    ],
                }

                # Map created_on to start_time for consistent sorting
                run_info['start_time'] = release.get('createdOn')
                run_info['queue_time'] = release.get('createdOn')

                result.append(run_info)

            return result

        except requests.exceptions.RequestException as e:
            logger.warning(
                f'Failed to get release pipeline runs for project {project_name}: {str(e)}'
            )
            return []

    def get_pipeline_logs(
        self,
        ctx: Context,
        project_name: str,
        run_id: str,
        log_id: Optional[str] = None,
        stage_name: Optional[str] = None,
        job_name: Optional[str] = None,
        pipeline_type: Optional[str] = 'build',
    ) -> ADOGetPipelineLogsResponse:
        """Get logs for a specific pipeline run or stage in Azure DevOps.

        Args:
            ctx: The FastMCP context
            project_name: Name of the project containing the pipeline
            run_id: ID of the pipeline run
            log_id: Optional specific log ID to retrieve
            stage_name: Optional stage name to filter logs
            job_name: Optional job name to filter logs
            pipeline_type: Type of pipeline ('build' or 'release', default: 'build')

        Returns:
            ADOGetPipelineLogsResponse containing the log content and metadata
        """
        try:
            # Validate required parameters
            if not project_name or not project_name.strip():
                raise ValueError('Project name is required')
            if not run_id or not run_id.strip():
                raise ValueError('Run ID is required')

            project_name = project_name.strip()
            run_id = run_id.strip()

            if pipeline_type == 'build':
                logs_info = self._get_build_logs(
                    project_name, run_id, log_id, stage_name, job_name
                )
            elif pipeline_type == 'release':
                logs_info = self._get_release_logs(
                    project_name, run_id, log_id, stage_name, job_name
                )
            else:
                raise ValueError(f'Unsupported pipeline type: {pipeline_type}')

            logger.info(
                f'Successfully retrieved logs for {pipeline_type} run {run_id} in project {project_name}'
            )
            logfire.info(
                'Retrieved Azure DevOps pipeline logs',
                project_name=project_name,
                run_id=run_id,
                pipeline_type=pipeline_type,
                log_id=log_id,
                stage_name=stage_name,
                job_name=job_name,
                organization_url=self.organization_url,
            )

            return ADOGetPipelineLogsResponse(
                status='success',
                message=f'Successfully retrieved logs for {pipeline_type} run {run_id}',
                logs=logs_info,
            )

        except requests.exceptions.RequestException as e:
            error_message = f'HTTP error while getting Azure DevOps pipeline logs: {str(e)}'
            logger.error(error_message)
            logfire.error('Failed to get Azure DevOps pipeline logs', error=str(e))

            return ADOGetPipelineLogsResponse(
                status='error',
                message=error_message,
                logs={},
            )
        except Exception as e:
            error_message = f'Error getting Azure DevOps pipeline logs: {str(e)}'
            logger.error(error_message)
            logfire.error('Failed to get Azure DevOps pipeline logs', error=str(e))

            return ADOGetPipelineLogsResponse(
                status='error',
                message=error_message,
                logs={},
            )

    def _get_build_logs(
        self,
        project_name: str,
        build_id: str,
        log_id: Optional[str] = None,
        stage_name: Optional[str] = None,
        job_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get build pipeline logs.

        Args:
            project_name: Name of the project
            build_id: ID of the build
            log_id: Optional specific log ID
            stage_name: Optional stage name filter
            job_name: Optional job name filter

        Returns:
            Dictionary containing log information
        """
        logs_info = {
            'run_id': build_id,
            'run_type': 'build',
            'logs': [],
            'total_logs': 0,
        }

        try:
            if log_id:
                # Get specific log
                api_url = f'{self.organization_url}{project_name}/_apis/build/builds/{build_id}/logs/{log_id}'
                params = {'api-version': '7.1'}

                response = requests.get(api_url, headers=self.headers, params=params, timeout=30)
                response.raise_for_status()

                log_content = response.text
                logs_info['logs'] = [
                    {
                        'id': log_id,
                        'content': log_content,
                        'size': len(log_content),
                    }
                ]
                logs_info['total_logs'] = 1

            else:
                # Get all logs for the build
                api_url = (
                    f'{self.organization_url}{project_name}/_apis/build/builds/{build_id}/logs'
                )
                params = {'api-version': '7.1'}

                response = requests.get(api_url, headers=self.headers, params=params, timeout=30)
                response.raise_for_status()

                data = response.json()
                log_entries = data.get('value', [])

                logs_info['total_logs'] = len(log_entries)

                # Filter logs by stage/job name if specified
                filtered_logs = []
                for log_entry in log_entries:
                    log_name = log_entry.get('name', '').lower()

                    # Apply filters
                    if stage_name and stage_name.lower() not in log_name:
                        continue
                    if job_name and job_name.lower() not in log_name:
                        continue

                    # Get the actual log content
                    try:
                        log_content_url = log_entry.get('url')
                        if log_content_url:
                            log_response = requests.get(
                                log_content_url, headers=self.headers, timeout=30
                            )
                            log_response.raise_for_status()
                            log_content = log_response.text
                        else:
                            log_content = 'Log content URL not available'

                        filtered_logs.append(
                            {
                                'id': log_entry.get('id'),
                                'name': log_entry.get('name'),
                                'type': log_entry.get('type'),
                                'url': log_entry.get('url'),
                                'created_on': log_entry.get('createdOn'),
                                'last_changed_on': log_entry.get('lastChangedOn'),
                                'line_count': log_entry.get('lineCount', 0),
                                'content': log_content,
                                'size': len(log_content),
                            }
                        )

                    except Exception as e:
                        logger.warning(
                            f'Failed to get content for log {log_entry.get("id")}: {str(e)}'
                        )
                        filtered_logs.append(
                            {
                                'id': log_entry.get('id'),
                                'name': log_entry.get('name'),
                                'type': log_entry.get('type'),
                                'url': log_entry.get('url'),
                                'created_on': log_entry.get('createdOn'),
                                'last_changed_on': log_entry.get('lastChangedOn'),
                                'line_count': log_entry.get('lineCount', 0),
                                'content': f'Error retrieving log content: {str(e)}',
                                'size': 0,
                            }
                        )

                logs_info['logs'] = filtered_logs

        except Exception as e:
            logger.error(f'Error getting build logs: {str(e)}')
            logs_info['error'] = str(e)

        return logs_info

    def _get_release_logs(
        self,
        project_name: str,
        release_id: str,
        log_id: Optional[str] = None,
        stage_name: Optional[str] = None,
        job_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get release pipeline logs.

        Args:
            project_name: Name of the project
            release_id: ID of the release
            log_id: Optional specific log ID
            stage_name: Optional stage name filter
            job_name: Optional job name filter

        Returns:
            Dictionary containing log information
        """
        logs_info = {
            'run_id': release_id,
            'run_type': 'release',
            'logs': [],
            'total_logs': 0,
        }

        try:
            # For releases, we need to get logs from deployment jobs
            # First get the release details to find environments/stages
            api_url = f'{self.organization_url}{project_name}/_apis/release/releases/{release_id}'
            params = {'api-version': '7.1', '$expand': 'environments'}

            response = requests.get(api_url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()

            release_data = response.json()
            environments = release_data.get('environments', [])

            all_logs = []
            for env in environments:
                env_name = env.get('name', '')
                env_id = env.get('id')

                # Apply stage filter
                if stage_name and stage_name.lower() not in env_name.lower():
                    continue

                # Get deployment jobs for this environment
                deploy_phases = env.get('deployPhasesSnapshot', [])
                for phase in deploy_phases:
                    phase_name = phase.get('name', '')

                    # Apply job filter
                    if job_name and job_name.lower() not in phase_name.lower():
                        continue

                    # Get tasks in this phase
                    deployment_jobs = phase.get('deploymentJobs', [])
                    for job in deployment_jobs:
                        job_id = job.get('job', {}).get('id')
                        if job_id:
                            try:
                                # Get logs for this job
                                logs_url = f'{self.organization_url}{project_name}/_apis/release/releases/{release_id}/environments/{env_id}/deployPhases/{phase.get("phaseId")}/tasks/{job_id}/logs'
                                logs_response = requests.get(
                                    logs_url,
                                    headers=self.headers,
                                    params={'api-version': '7.1'},
                                    timeout=30,
                                )

                                if logs_response.status_code == 200:
                                    log_content = logs_response.text
                                    all_logs.append(
                                        {
                                            'id': f'{env_id}_{phase.get("phaseId")}_{job_id}',
                                            'name': f'{env_name} - {phase_name} - {job.get("job", {}).get("name", "")}',
                                            'environment': env_name,
                                            'phase': phase_name,
                                            'job': job.get('job', {}).get('name', ''),
                                            'content': log_content,
                                            'size': len(log_content),
                                            'status': job.get('job', {}).get('status'),
                                        }
                                    )
                            except Exception as e:
                                logger.warning(f'Failed to get logs for job {job_id}: {str(e)}')
                                all_logs.append(
                                    {
                                        'id': f'{env_id}_{phase.get("phaseId")}_{job_id}',
                                        'name': f'{env_name} - {phase_name} - {job.get("job", {}).get("name", "")}',
                                        'environment': env_name,
                                        'phase': phase_name,
                                        'job': job.get('job', {}).get('name', ''),
                                        'content': f'Error retrieving log content: {str(e)}',
                                        'size': 0,
                                        'status': job.get('job', {}).get('status'),
                                    }
                                )

            logs_info['logs'] = all_logs
            logs_info['total_logs'] = len(all_logs)

        except Exception as e:
            logger.error(f'Error getting release logs: {str(e)}')
            logs_info['error'] = str(e)

        return logs_info

    def rerun_pipeline_stage(
        self,
        ctx: Context,
        project_name: str,
        run_id: str,
        stage_name: Optional[str] = None,
        stage_id: Optional[str] = None,
        pipeline_type: Optional[str] = 'build',
    ) -> ADORerunPipelineStageResponse:
        """Rerun a specific stage of a pipeline in Azure DevOps.

        Args:
            ctx: The FastMCP context
            project_name: Name of the project containing the pipeline
            run_id: ID of the original pipeline run
            stage_name: Optional name of the stage to rerun
            stage_id: Optional ID of the stage to rerun (takes precedence over name)
            pipeline_type: Type of pipeline ('build' or 'release', default: 'build')

        Returns:
            ADORerunPipelineStageResponse containing information about the rerun operation
        """
        try:
            # Validate required parameters
            if not project_name or not project_name.strip():
                raise ValueError('Project name is required')
            if not run_id or not run_id.strip():
                raise ValueError('Run ID is required')

            project_name = project_name.strip()
            run_id = run_id.strip()

            if pipeline_type == 'build':
                rerun_info = self._rerun_build_stage(project_name, run_id, stage_name, stage_id)
            elif pipeline_type == 'release':
                rerun_info = self._rerun_release_stage(project_name, run_id, stage_name, stage_id)
            else:
                raise ValueError(f'Unsupported pipeline type: {pipeline_type}')

            logger.info(
                f'Successfully initiated rerun for {pipeline_type} stage in run {run_id} in project {project_name}'
            )
            logfire.info(
                'Reran Azure DevOps pipeline stage',
                project_name=project_name,
                run_id=run_id,
                pipeline_type=pipeline_type,
                stage_name=stage_name,
                stage_id=stage_id,
                organization_url=self.organization_url,
            )

            return ADORerunPipelineStageResponse(
                status='success',
                message=f'Successfully initiated rerun for {pipeline_type} stage in run {run_id}',
                rerun_info=rerun_info,
            )

        except requests.exceptions.RequestException as e:
            error_message = f'HTTP error while rerunning Azure DevOps pipeline stage: {str(e)}'
            logger.error(error_message)
            logfire.error('Failed to rerun Azure DevOps pipeline stage', error=str(e))

            return ADORerunPipelineStageResponse(
                status='error',
                message=error_message,
                rerun_info={},
            )
        except Exception as e:
            error_message = f'Error rerunning Azure DevOps pipeline stage: {str(e)}'
            logger.error(error_message)
            logfire.error('Failed to rerun Azure DevOps pipeline stage', error=str(e))

            return ADORerunPipelineStageResponse(
                status='error',
                message=error_message,
                rerun_info={},
            )

    def _rerun_build_stage(
        self,
        project_name: str,
        build_id: str,
        stage_name: Optional[str] = None,
        stage_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Rerun a build pipeline stage.

        Args:
            project_name: Name of the project
            build_id: ID of the build
            stage_name: Optional stage name
            stage_id: Optional stage ID

        Returns:
            Dictionary containing rerun information
        """
        try:
            # For build pipelines, we typically need to rerun the entire build
            # as Azure DevOps doesn't support partial reruns for most build types
            # However, we can retry specific jobs or stages in some cases

            # First, get the original build information
            api_url = f'{self.organization_url}{project_name}/_apis/build/builds/{build_id}'
            params = {'api-version': '7.1'}

            response = requests.get(api_url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()

            build_data = response.json()
            definition_id = build_data.get('definition', {}).get('id')
            source_branch = build_data.get('sourceBranch')
            source_version = build_data.get('sourceVersion')

            if not definition_id:
                raise ValueError('Could not determine pipeline definition ID from original build')

            # Create a new build with the same parameters
            rerun_url = f'{self.organization_url}{project_name}/_apis/build/builds'
            rerun_body = {
                'definition': {'id': definition_id},
                'sourceBranch': source_branch,
                'sourceVersion': source_version,
                'reason': 'manual',
                'parameters': build_data.get('parameters', '{}'),
            }

            rerun_response = requests.post(
                rerun_url,
                headers=self.headers,
                params={'api-version': '7.1'},
                json=rerun_body,
                timeout=30,
            )
            rerun_response.raise_for_status()

            new_build_data = rerun_response.json()

            return {
                'original_run_id': build_id,
                'new_run_id': new_build_data.get('id'),
                'new_run_number': new_build_data.get('buildNumber'),
                'status': new_build_data.get('status'),
                'queue_time': new_build_data.get('queueTime'),
                'url': new_build_data.get('url'),
                'web_url': new_build_data.get('_links', {}).get('web', {}).get('href'),
                'pipeline_type': 'build',
                'stage_rerun_method': 'full_pipeline',
                'note': 'Build pipelines are rerun entirely as stage-specific reruns are not supported',
            }

        except Exception as e:
            logger.error(f'Error rerunning build stage: {str(e)}')
            return {
                'original_run_id': build_id,
                'error': str(e),
                'pipeline_type': 'build',
            }

    def _rerun_release_stage(
        self,
        project_name: str,
        release_id: str,
        stage_name: Optional[str] = None,
        stage_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Rerun a release pipeline stage.

        Args:
            project_name: Name of the project
            release_id: ID of the release
            stage_name: Optional stage name
            stage_id: Optional stage ID

        Returns:
            Dictionary containing rerun information
        """
        try:
            # First, get the release details to find the stage/environment
            api_url = f'{self.organization_url}{project_name}/_apis/release/releases/{release_id}'
            params = {'api-version': '7.1', '$expand': 'environments'}

            response = requests.get(api_url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()

            release_data = response.json()
            environments = release_data.get('environments', [])

            target_environment = None

            if stage_id:
                # Find environment by ID
                target_environment = next(
                    (env for env in environments if str(env.get('id')) == str(stage_id)), None
                )
            elif stage_name:
                # Find environment by name
                target_environment = next(
                    (
                        env
                        for env in environments
                        if env.get('name', '').lower() == stage_name.lower()
                    ),
                    None,
                )
            else:
                # If no stage specified, find the first failed environment
                target_environment = next(
                    (
                        env
                        for env in environments
                        if env.get('status') in ['failed', 'canceled', 'rejected']
                    ),
                    None,
                )

            if not target_environment:
                if stage_name or stage_id:
                    raise ValueError(
                        f'Stage "{stage_name or stage_id}" not found in release {release_id}'
                    )
                else:
                    raise ValueError(f'No failed stages found to rerun in release {release_id}')

            env_id = target_environment.get('id')
            env_name = target_environment.get('name')

            # Redeploy the environment
            redeploy_url = f'{self.organization_url}{project_name}/_apis/release/releases/{release_id}/environments/{env_id}/deployments'
            redeploy_body = {
                'comment': f'Redeploying environment {env_name} via MCP server',
            }

            redeploy_response = requests.post(
                redeploy_url,
                headers=self.headers,
                params={'api-version': '7.1'},
                json=redeploy_body,
                timeout=30,
            )
            redeploy_response.raise_for_status()

            deployment_data = redeploy_response.json()

            return {
                'original_run_id': release_id,
                'environment_id': env_id,
                'environment_name': env_name,
                'deployment_id': deployment_data.get('id'),
                'status': deployment_data.get('operationStatus'),
                'started_on': deployment_data.get('startedOn'),
                'pipeline_type': 'release',
                'stage_rerun_method': 'environment_redeploy',
                'comment': redeploy_body.get('comment'),
            }

        except Exception as e:
            logger.error(f'Error rerunning release stage: {str(e)}')
            return {
                'original_run_id': release_id,
                'error': str(e),
                'pipeline_type': 'release',
            }
