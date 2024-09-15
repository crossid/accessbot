import asyncio
import logging
from collections import Counter
from typing import Any

from langchain.prompts.chat import ChatPromptTemplate, SystemMessagePromptTemplate
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel

from app.embeddings import create_embedding
from app.llm.model import create_model
from app.llm.tools.user_data.factory import GetUserDataFactory
from app.llm.tools.user_data.iface import UserDataInterface
from app.models import Application, Workspace
from app.services import factory_dir_store
from app.settings import settings
from app.sql import SQLAlchemyTransactionContext
from app.vector_store import create_workspace_vstore

logger = logging.getLogger(__name__)


def calculate_access_density(data: dict[str, list[str]]):
    # Flatten all access objects into a single list
    all_access = [access for user_access in data.values() for access in user_access]

    # Count occurrences of each access ID
    access_counts = Counter(access.id for access in all_access)

    # Calculate total number of users
    total_users = len(data)

    # Calculate density for each access ID and update UserAccess objects
    access_density = {}
    for access in all_access:
        if access.id not in access_density:
            density = access_counts[access.id] / total_users
            updated_access = access.model_copy(update={"density": density})
            access_density[access.id] = updated_access

    return access_density


def dict_to_md(data: dict[str, Any]) -> str:
    md_lines = []
    for key, value in data.items():
        md_lines.append(f"**{key}**: {value}")
    return "\n".join(md_lines)


def prepare_retriever(ws: Workspace, top_k: int, min_relevance: float):
    vstore = create_workspace_vstore(
        workspace_id=ws.id,
        embedding=create_embedding(settings.VSTORE_EMBEDDING),
        workspace_name=ws.name,
    )

    ret = vstore.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={
            "k": top_k,
            # "fetch_k": max(40, top_k * 2),
            "score_threshold": min_relevance,
            "filter": {"type": "user"},
        },
    )

    return ret


async def safe_get_user_access(udf: UserDataInterface, email: str, app_name: str):
    try:
        user_access = await udf.get_user_access(user_email=email, app_names=[app_name])
        return {email: user_access[app_name] or []}
    except Exception as e:
        logger.info(f"failed to fetch user access {str(e)}")
        return {email: []}


def get_sys_msg():
    sys_msg = """
You are a helpful assistant that takes in user data and outputs a list of access groups that the user has.
Here is the access level density for the 10 closest users: {access_density}
Here is the business logic:
<business_logic>
{business_logic}
</business_logic>

Rank the access groups relevancy to the user based on the access level density and the business logic, with a score of 0-10.
0 is not relevant at all, 10 is the most relevant.
explain your reasoning for the score.

Remember: if there are no access groups to choose from, return an empty array.

example output:
[
    {{"access_group": "access_group_name", "score": 100, "explanation": "reasoning for the score"}},
    {{"access_group": "access_group_name", "score": 90, "explanation": "reasoning for the score"}},
    {{"access_group": "access_group_name", "score": 80, "explanation": "reasoning for the score"}},
]
"""
    return SystemMessagePromptTemplate.from_template(template=sys_msg)


class UserAccessPrediction(BaseModel):
    app_name: str
    prediction: str


async def predict_access_to_user(
    user_md: str,
    ws: Workspace,
    app: Application,
    top_k: int = 10,
    min_relevance: float = 0.7,
) -> UserAccessPrediction:
    """
    returns a tuple of app_name to the prediction response
    """

    dir_store = factory_dir_store()
    with SQLAlchemyTransactionContext().manage() as tx_context:
        dir = dir_store.get_by_id(
            directory_id=app.read_directory_id,
            workspace_id=ws.id,
            tx_context=tx_context,
        )

        if dir is None:
            raise ValueError(f"no read connection for app {app.name}")

    ret = prepare_retriever(ws=ws, top_k=top_k, min_relevance=min_relevance)
    docs = ret.invoke(user_md)
    similar_users_emails = [doc.metadata["email"] for doc in docs]

    udf: UserDataInterface = GetUserDataFactory(workspace=ws, directory=dir)
    user_access_tasks = [
        safe_get_user_access(udf=udf, email=email, app_name=app.name)
        for email in similar_users_emails
    ]
    results = await asyncio.gather(*user_access_tasks)

    # Combine all results into a single dictionary
    combined_results = {}
    for result in results:
        combined_results.update(result)

    # Call calculate_access_density
    access_density = calculate_access_density(combined_results)
    sys_msg = get_sys_msg()

    model = create_model(temperature=0.5)
    parser = StrOutputParser()

    msg = HumanMessage(content=f"predict for user:{user_md}")
    prompt = ChatPromptTemplate.from_messages([sys_msg, msg])

    chain = prompt | model | parser
    response = await chain.ainvoke(
        {
            "access_density": access_density,
            "business_logic": app.business_instructions or "no special instructions",
        }
    )
    return UserAccessPrediction(app_name=app.name, prediction=response)


def user_access_predictions_to_llm_format(predictions: list[UserAccessPrediction]):
    header = "User Access Predictions:\n\n"
    items = "\n".join(
        f"App: {p.app_name}\nPrediction: {p.prediction}\n" for p in predictions
    )
    footer = "\nPlease summarize the access predictions above."
    return header + items + footer


async def format_response(
    predictions: list[UserAccessPrediction], output_instructions: str
):
    sys_msg = SystemMessagePromptTemplate.from_template(
        template="""
You are a helpful summarization and formatting assistant. 
You'll get a text explaining access groups relevancy to a user from different applications.
Your task is to summarize and format the input text according to the output instructions.
Remember: include all access groups and all applications.

<output_instructions>
{output_instructions}
</output_instructions>
"""
    )

    model = create_model(temperature=0.7)
    parser = StrOutputParser()

    msg = HumanMessage(content=user_access_predictions_to_llm_format(predictions))
    prompt = ChatPromptTemplate.from_messages([sys_msg, msg])

    chain = prompt | model | parser
    response = await chain.ainvoke({"output_instructions": output_instructions})

    return response
