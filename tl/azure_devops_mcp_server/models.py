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
