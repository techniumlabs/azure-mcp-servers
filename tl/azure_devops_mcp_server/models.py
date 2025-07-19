from typing import Any, Dict, List


class ADOListProjectsResponse(Dict[str, Any]):
    """Response model for listing projects in Azure DevOps."""

    def __init__(self, status: str, message: str, projects: List[Dict[str, Any]], count: int):
        """Initialize Azure DevOps projects response.

        Args:
            status: Status of the operation (success/error)
            message: Message describing the result
            projects: List of project information
            count: Number of projects returned
        """
        super().__init__(
            {'status': status, 'message': message, 'projects': projects, 'count': count}
        )
        self.status = status
        self.message = message
        self.projects = projects
        self.count = count


class ADOListPipelinesResponse(Dict[str, Any]):
    """Response model for listing pipelines in Azure DevOps."""

    def __init__(self, status: str, message: str, pipelines: List[Dict[str, Any]], count: int):
        """Initialize Azure DevOps pipelines response.

        Args:
            status: Status of the operation (success/error)
            message: Message describing the result
            pipelines: List of pipeline information
            count: Number of pipelines returned
        """
        super().__init__(
            {'status': status, 'message': message, 'pipelines': pipelines, 'count': count}
        )
        self.status = status
        self.message = message
        self.pipelines = pipelines
        self.count = count


class ADORunPipelineResponse(Dict[str, Any]):
    """Response model for running a pipeline in Azure DevOps."""

    def __init__(self, status: str, message: str, run_info: Dict[str, Any]):
        """Initialize Azure DevOps run pipeline response.

        Args:
            status: Status of the operation (success/error)
            message: Message describing the result
            run_info: Information about the pipeline run that was triggered
        """
        super().__init__({'status': status, 'message': message, 'run_info': run_info})
        self.status = status
        self.message = message
        self.run_info = run_info


class ADOCreateProjectResponse(Dict[str, Any]):
    """Response model for creating a project in Azure DevOps."""

    def __init__(self, status: str, message: str, project_info: Dict[str, Any]):
        """Initialize Azure DevOps create project response.

        Args:
            status: Status of the operation (success/error)
            message: Message describing the result
            project_info: Information about the created project or operation details
        """
        super().__init__({'status': status, 'message': message, 'project_info': project_info})
        self.status = status
        self.message = message
        self.project_info = project_info


class ADOListRepositoriesResponse(Dict[str, Any]):
    """Response model for listing repositories in Azure DevOps."""

    def __init__(self, status: str, message: str, repositories: List[Dict[str, Any]], count: int):
        """Initialize Azure DevOps repositories response.

        Args:
            status: Status of the operation (success/error)
            message: Message describing the result
            repositories: List of repository information
            count: Number of repositories returned
        """
        super().__init__(
            {'status': status, 'message': message, 'repositories': repositories, 'count': count}
        )
        self.status = status
        self.message = message
        self.repositories = repositories
        self.count = count


class ADOListPullRequestsResponse(Dict[str, Any]):
    """Response model for listing pull requests in Azure DevOps."""

    def __init__(self, status: str, message: str, pull_requests: List[Dict[str, Any]], count: int):
        """Initialize Azure DevOps pull requests response.

        Args:
            status: Status of the operation (success/error)
            message: Message describing the result
            pull_requests: List of pull request information
            count: Number of pull requests returned
        """
        super().__init__(
            {'status': status, 'message': message, 'pull_requests': pull_requests, 'count': count}
        )
        self.status = status
        self.message = message
        self.pull_requests = pull_requests
        self.count = count


class ADOListBranchesResponse(Dict[str, Any]):
    """Response model for listing branches in Azure DevOps repository."""

    def __init__(self, status: str, message: str, branches: List[Dict[str, Any]], count: int):
        """Initialize Azure DevOps branches response.

        Args:
            status: Status of the operation (success/error)
            message: Message describing the result
            branches: List of branch information
            count: Number of branches returned
        """
        super().__init__(
            {'status': status, 'message': message, 'branches': branches, 'count': count}
        )
        self.status = status
        self.message = message
        self.branches = branches
        self.count = count


class ADOCreateRepositoryResponse(Dict[str, Any]):
    """Response model for creating a repository in Azure DevOps."""

    def __init__(self, status: str, message: str, repository_info: Dict[str, Any]):
        """Initialize Azure DevOps create repository response.

        Args:
            status: Status of the operation (success/error)
            message: Message describing the result
            repository_info: Information about the created repository
        """
        super().__init__(
            {'status': status, 'message': message, 'repository_info': repository_info}
        )
        self.status = status
        self.message = message
        self.repository_info = repository_info


class ADOCreatePullRequestResponse(Dict[str, Any]):
    """Response model for creating a pull request in Azure DevOps."""

    def __init__(self, status: str, message: str, pull_request_info: Dict[str, Any]):
        """Initialize Azure DevOps create pull request response.

        Args:
            status: Status of the operation (success/error)
            message: Message describing the result
            pull_request_info: Information about the created pull request
        """
        super().__init__(
            {'status': status, 'message': message, 'pull_request_info': pull_request_info}
        )
        self.status = status
        self.message = message
        self.pull_request_info = pull_request_info


class ADOListPipelineRunsResponse(Dict[str, Any]):
    """Response model for listing pipeline runs in Azure DevOps."""

    def __init__(self, status: str, message: str, runs: List[Dict[str, Any]], count: int):
        """Initialize Azure DevOps pipeline runs response.

        Args:
            status: Status of the operation (success/error)
            message: Message describing the result
            runs: List of pipeline run information
            count: Number of pipeline runs returned
        """
        super().__init__({'status': status, 'message': message, 'runs': runs, 'count': count})
        self.status = status
        self.message = message
        self.runs = runs
        self.count = count


class ADOGetPipelineLogsResponse(Dict[str, Any]):
    """Response model for getting pipeline stage logs in Azure DevOps."""

    def __init__(self, status: str, message: str, logs: Dict[str, Any]):
        """Initialize Azure DevOps pipeline logs response.

        Args:
            status: Status of the operation (success/error)
            message: Message describing the result
            logs: Log information including content and metadata
        """
        super().__init__({'status': status, 'message': message, 'logs': logs})
        self.status = status
        self.message = message
        self.logs = logs


class ADORerunPipelineStageResponse(Dict[str, Any]):
    """Response model for rerunning a pipeline stage in Azure DevOps."""

    def __init__(self, status: str, message: str, rerun_info: Dict[str, Any]):
        """Initialize Azure DevOps rerun pipeline stage response.

        Args:
            status: Status of the operation (success/error)
            message: Message describing the result
            rerun_info: Information about the rerun operation
        """
        super().__init__({'status': status, 'message': message, 'rerun_info': rerun_info})
        self.status = status
        self.message = message
        self.rerun_info = rerun_info
