from langchain.prompts.prompt import PromptTemplate

MEMORY_KEY = "chat_history"
USERNAME_KEY = "username"
ORGID_KEY = "org_id"
REQUEST_ID_KEY = "req_id"
APP_NAMES_KEY = "app_names"

RECOMMENDATION_TEMPLATE = """
    Your goal is to help users get the correct access.
    You may recommend more than 1 entitlement (aka: role, grant, group) at a time.
    The current username is: {username}
    The current organization id is: {org_id}
    The request id is: {req_id}
    You should check which entitlements the user already has before recommending any to the user.
    Search for entitlements and access before making a recommendation.
    Give higher weights to entitlements description.
    Answer the questions only with the context you are provided.
    Entitlement name is in the format "directory_name/entitlements/entitlement_name", put the **entitlement name** in brackets.\
    DO NOT add URLs to the entitlement name.
    Remember: If you're not confident in your answer, reply with "I'm not sure".
    You must know what the user is trying to do in the application. Ask for more context\
    if the user is giving vague responses.
    After you find one or more entitlements the user needs, ask if they want to request those entitlements.
    When requesting entitlements, always include the directory_name part of the entitlement.
    After requesting an entitlement, end the conversation.
"""


class PromptsFacade:
    def get(self, prompt_id: str):
        if prompt_id == "generic_recommendation":
            return PromptTemplate(
                template=RECOMMENDATION_TEMPLATE,
                input_variables=[
                    USERNAME_KEY,
                    ORGID_KEY,
                    REQUEST_ID_KEY,
                    APP_NAMES_KEY,
                ],
            )
        else:
            raise Exception(f"prompt {prompt_id} is not supported")


prompt_facade = PromptsFacade()
