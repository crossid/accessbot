from app.models import User

from .iface import TicketInterface


class JiraTicketImpl(TicketInterface):
    project: str
    issuetype: str
    tenant: str
    username: str
    password: str

    def __init__(self, project, issuetype, tenant, username, password) -> None:
        try:
            from atlassian import Jira
        except ImportError:
            raise ImportError(
                "Could not import atlassian package. "
                "Please install it with `pip install atlassian-python-api`."
            )

        self.project = project
        self.issuetype = issuetype
        self.client = Jira(
            url=f"https://{tenant}.atlassian.net", username=username, password=password
        )

    def create_ticket(
        self,
        content: str,
        owner: User,
        requester: User,
        app_name: str,
        conv_summary: str,
        conversation_id: str,
        workspace_id: str,
        **kwargs,
    ) -> str:
        # JIRA Tickets can't have \n in them.
        fields = dict(
            summary=content,
            project=dict(key=self.project),
            issuetype=dict(name=self.issuetype),
        )

        result = self.client.create_issue(fields)
        return result
