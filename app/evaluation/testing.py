import argparse

import injector
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langsmith.evaluation import LangChainStringEvaluator, evaluate
from langsmith.schemas import Example, Run

from app.embeddings import create_embedding
from app.llm.conversation import prepare_known_apps_str
from app.llm.graph import CONVERSATION_TYPE_KEY, create_graph
from app.llm.prompts import (
    CONVERSATION_ID_KEY,
    KNOWN_APPS_KEY,
    MEMORY_KEY,
    USER_EMAIL_KEY,
    WS_ID_KEY,
)
from app.llm.tools.create_ticket_for_role_request_tool import request_roles_tool as rrt
from app.llm.tools.provision_role_tool import provision_roles_tool as prt
from app.models import Application
from app.models_stores import (
    ApplicationStore,
    ChatMessageStore,
    ConversationStore,
    UserStore,
    WorkspaceStore,
)
from app.services import set_service_registry
from app.vault import VaultAPI
from app.vault_env_vars import EnvVarVault
from app.vector_store import create_retriever

from .stores import (
    SINGLE_USER_EMAIL,
    ApplicationStoreMock,
    ChatMessageStoreMock,
    ConversationStoreMock,
    UserStoreMock,
    WorkspaceStoreMock,
)

load_dotenv()


def must_mention(run: Run, example: Example) -> dict:
    prediction = run.outputs.get("output") or ""
    words_in_prediction = prediction.split()
    required = example.outputs.get("must_mention") or []
    score = sum(1 for word in words_in_prediction if word in required) / len(required)
    return {"key": "must_mention", "score": score}


def create_graph_for_test(ws_id, conv_id, retriever):
    dc = {
        USER_EMAIL_KEY: SINGLE_USER_EMAIL,
        WS_ID_KEY: ws_id,
        CONVERSATION_ID_KEY: conv_id,
        KNOWN_APPS_KEY: prepare_known_apps_str(
            apps=[
                Application(
                    id="1",
                    display_name="fooquery",
                    aliases=["fquery", "fq"],
                    workspace_id=ws_id,
                    extra_instructions="bla bla bla",
                )
            ]
        ),
    }

    memory = SqliteSaver.from_conn_string(":memory:")
    graph = create_graph(
        tools=[rrt, prt], data_context=dc, retriever=retriever, checkpointer=memory
    )
    return graph


def predict_for_ws(ws_id):
    embedding = create_embedding()
    retriever = create_retriever(workspace_id=ws_id, embedding=embedding)

    def predict(inputs: dict) -> dict:
        conv_id = "abcd"
        graph = create_graph_for_test(ws_id=ws_id, conv_id=conv_id, retriever=retriever)
        config = {
            "configurable": {
                "thread_id": conv_id,
                "workspace_id": ws_id,
            }
        }
        messages = inputs[MEMORY_KEY]
        result = graph.invoke(
            {
                MEMORY_KEY: messages,
                CONVERSATION_TYPE_KEY: inputs[CONVERSATION_TYPE_KEY],
            },
            config,
        )
        last_message = result[MEMORY_KEY][-1].content
        return {"output": last_message}

    return predict


def prepare_data(run: Run, example: Example):
    return {
        "prediction": run.outputs.get("output") or "",
        "reference": example.outputs.get("expected") or "",
        "input": example.inputs.get(MEMORY_KEY) or [],
    }


def run_evaluation(ws_id, dataset="default"):
    eval_llm = ChatOpenAI(model="gpt-4", temperature=0)
    experiment_results = evaluate(
        predict_for_ws(ws_id=ws_id),  # Your AI system
        data=dataset,  # The data to predict and grade over
        evaluators=[
            must_mention,
            LangChainStringEvaluator(
                "labeled_criteria",
                config={
                    "criteria": {
                        "usefulness": "The prediction is useful if...",
                    },
                    "llm": eval_llm,
                },
                prepare_data=prepare_data,
            ),
        ],  # The evaluators to score the results
        experiment_prefix="testing_information_node",
        metadata={
            "version": "0.0.1",
        },
    )
    print(experiment_results)


"""
    poetry run evaluation "Info Gather Dataset" -ws=dsadsa
"""


class TestModule(injector.Module):
    def configure(self, binder):
        binder.bind(WorkspaceStore, to=WorkspaceStoreMock, scope=injector.singleton)
        binder.bind(
            ConversationStore, to=ConversationStoreMock, scope=injector.singleton
        )
        binder.bind(ChatMessageStore, to=ChatMessageStoreMock, scope=injector.singleton)
        binder.bind(UserStore, to=UserStoreMock, scope=injector.singleton)
        binder.bind(VaultAPI, to=EnvVarVault, scope=injector.singleton)
        binder.bind(ApplicationStore, to=ApplicationStoreMock, scope=injector.singleton)


def start():
    # All the logic of argparse goes in this function
    parser = argparse.ArgumentParser(description="Run Evaluation")
    parser.add_argument("dataset", type=str, help="name of the dataset")
    parser.add_argument("-ws", type=str, help="workspace id")

    args = parser.parse_args()

    service_registry = injector.Injector([TestModule()])
    set_service_registry(service_registry)

    if args.ws is None:
        args.ws = "IDro10K0ux"
    run_evaluation(dataset=args.dataset, ws_id=args.ws)
