from langchain.prompts.prompt import PromptTemplate

MEMORY_KEY = "chat_history"
USER_EMAIL_KEY = "email"
WS_ID_KEY = "workspace_id"
CONVERSATION_ID_KEY = "conversation_id"
APP_NAMES_KEY = "app_names"

RECOMMENDATION_TEMPLATE = """
    Your only goal is to help users get the correct access.
    You may recommend more than 1 entitlement (aka: role, grant, group) at a time.
    The current user email is: {email}
    The current workspace id is: {workspace_id}
    The conversation id is: {conversation_id}
    Answer the questions only with the provided context.
    Entitlement name is in the format `directory_name/entitlements/entitlement_name`, put the **entitlement name** in brackets.\
    DO NOT add URLs to the entitlement name.
    Remember: If you're not confident in your answer, reply with "I'm not sure".
    You must know what the user is trying to do in the application. Ask for more context
    if the user is giving vague responses.
"""

DATA_OWNER_TEMPLATE = """
    Your goal is to help data owners approve role access requested by users.
    The current user email is: {email}
    The current workspace id is: {workspace_id}
    The conversation id is: {conversation_id}
"""


class PromptsStore:
    def get(self, prompt_id: str):
        if prompt_id == "generic_recommendation":
            return PromptTemplate(
                template=RECOMMENDATION_TEMPLATE,
                input_variables=[
                    USER_EMAIL_KEY,
                    WS_ID_KEY,
                    CONVERSATION_ID_KEY,
                ],
            )
        elif prompt_id == "data_owner":
            return PromptTemplate(
                template=DATA_OWNER_TEMPLATE,
                input_variables=[
                    USER_EMAIL_KEY,
                    WS_ID_KEY,
                    CONVERSATION_ID_KEY,
                ],
            )
        else:
            raise Exception(f"prompt {prompt_id} is not supported")


prompt_store = PromptsStore()
