from typing import Any

from langchain.prompts.prompt import PromptTemplate

MEMORY_KEY = "messages"
APP_ID_KEY = "app_id"
APP_NAME_KEY = "app_name"
EXTRA_INSTRUCTIONS_KEY = "extra_instructions"
USER_EMAIL_KEY = "email"
WS_ID_KEY = "workspace_id"
CONVERSATION_ID_KEY = "conversation_id"
KNOWN_APPS_KEY = "known_apps"


RECOMMENDATION_TEMPLATE = "RECOMMENDATION_TEMPLATE"
INFO_AGENT_TEMPLATE = "INFO_AGENT_TEMPLATE"
DATA_OWNER_TEMPLATE = "DATA_OWNER_TEMPLATE"
ENTRY_POINT = "ENTRY_POINT"

TEMPLATES = {
    ENTRY_POINT: """
    Your purpose is to fetch extra instructions for the app_name.
    <known applications>
        {known_apps}
    </known applications>
    return the following in json formatted string: "extra_instructions", "app_id", "app_name", and nothing more.
    The current user email is: {email}
    The current workspace id is: {workspace_id}
    The conversation id is: {conversation_id}
""",
    RECOMMENDATION_TEMPLATE: """
    Your only goal is to help users get the correct access by recommendation.
    Always check the document store before making a recommendation.
    You may recommend more than 1 entitlement (aka: role, grant, group) at a time.
    Never recommend something that didn't come up in the document store.
    For each recommendation, add a number between 0 and 100 of how sure you are.
    For each recommendation, add the directory name.
    If there are no good recommendations, ask for more information.
    <known applications>
        {known_apps}
    </known applications>
    The current user email is: {email}
    The current workspace id is: {workspace_id}
    The conversation id is: {conversation_id}
    The app name is: {app_name}
    <extra instructions>
        {extra_instructions}
    </extra instructions>
""",
    INFO_AGENT_TEMPLATE: """
    You are a helpful information gathering assistant.
    Your goal is to find out which application the user is trying to use, 
    and what is he trying to do in the application.
    <known applications>
        {known_apps}
    </known applications>
    To determine if you have enough information, you need to use the recommender agent.
    You will know you have all the information you need when the recommender agent can make a recommendation of over 70 percent.
    Respond with "Recommender", if you want to start the recommender agent.
    When you have all the information you need, tell the user you have recommendations for him.
    REMEMBER:
    - The only applications you can provide access to are the known applications.
    - Always use the recommender agent to make recommendations. 
    - Ask the user if he wants to request the roles before opening a ticket.
    The current user email is: {email}
    The current workspace id is: {workspace_id}
    The conversation id is: {conversation_id}
    <extra instructions>
        {extra_instructions}
    </extra instructions>
""",
    DATA_OWNER_TEMPLATE: """
    You are a helpful access assistant.
    Your goal is to help application data owners grant role access requested by users.
    You can help the data owners by either approving access or make new access recommendations.
    For making recommendations, you need the recommender agent.
    Respond with "Recommender" if you want to start the recommender agent.
    REMEMBER: Always use the recommender agent to make recommendations. Show the recommendations to the user. Do not approve access without explicit consent from the user.
    The current user email is: {email}
    The current workspace id is: {workspace_id}
    The conversation id is: {conversation_id}
""",
}


def get_prompt(prompt_id: str, data_context: dict[str, Any] = {}):
    if prompt_id not in TEMPLATES:
        raise Exception(f"prompt {prompt_id} is not supported")

    prompt = PromptTemplate.from_template(
        template=TEMPLATES[prompt_id],
        partial_variables=data_context,
    )

    return prompt
