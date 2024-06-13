import enum
from typing import List

from langchain_core.messages import HumanMessage
from pydantic.v1 import BaseModel, Field

from app.llm.agents import create_agent
from app.llm.prompts import MEMORY_KEY
from app.llm.tools.rule_engine.rule_engine_relevant_data import (
    create_relevant_data_tool,
)
from app.models import Application, Directory, Rule, RuleTypes, ThenTypes, Workspace
from app.services import factory_rule_store
from app.sql import SQLAlchemyTransactionContext


class FinalAnswer(enum.Enum):
    approve = "approve"
    deny = "deny"


class RulesAnswer(BaseModel):
    final_answer: FinalAnswer = Field(
        description="are any of the rules correct? approve/deny"
    )
    rules: List[str] = Field(description="list of correct rules")
    why: str = Field(description="explanation of the decision")
    final_decision_rule: str = Field(
        description="the rule that made you take your final decision"
    )


prompt_template = """
  You are a rule engine assistant.
  Your goal is to determine if any of the provided rules are correct.
  <approve_rules>
    {approve_rules}
  </approve_rules>
  <deny_rules>
    {deny_rules}
  </deny_rules>

  Default to "deny"
  
  Answer with a dictionary containing the fields:
    - final_answer: should be approve or deny
    - rules: list of from approve_rules or deny_rules that match
    - why: explanation for your decision
    - final_decision_rule: the rule that made you take your final decision
"""


# engine is here for easier testing
def get_rules(
    ws_id: str, dir_id: str, app_id: str, tx_context
) -> dict[str, List[Rule]]:
    rule_store = factory_rule_store()
    approve_rules = []
    deny_rules = []
    ws_rules, _ = rule_store.list(
        workspace_id=ws_id,
        limit=9999,
        tx_context=tx_context,
        filters={"type": RuleTypes.auto_approve},
    )

    for rule in ws_rules:
        r_dir_ids = rule.directory_ids
        r_app_ids = rule.application_ids
        if (
            (r_app_ids is None and r_dir_ids is None)
            or (r_app_ids is None and dir_id in r_dir_ids)
            or (r_dir_ids is None and app_id in r_app_ids)
        ):
            if rule.then == ThenTypes.approve:
                approve_rules.append(rule)
            else:
                deny_rules.append(rule)

    return {"approve_rules": approve_rules, "deny_rules": deny_rules}


def rules_to_prompt_str(rules: dict[str, List[Rule]]) -> dict[str, str]:
    approve_rules_str = (
        f"{"\n".join([f"- {rule.when}" for rule in rules["approve_rules"]])}"
    )
    deny_rules_str = f"{"\n".join([f"- {rule.when}" for rule in rules["deny_rules"]])}"

    return {"approve_rules": approve_rules_str, "deny_rules": deny_rules_str}


def should_auto_approve(
    ws: Workspace, dir: Directory, app: Application, user_email: str, **kwargs
) -> RulesAnswer:
    # get rules
    with SQLAlchemyTransactionContext().manage() as tx_context:
        rules = get_rules(
            ws_id=ws.id, dir_id=dir.id, app_id=app.id, tx_context=tx_context
        )
        if len(rules) == 0:
            return RulesAnswer(
                final_answer=FinalAnswer.deny,
                rules=[],
                why="no rules defined for this ws/dir/app",
                final_decision_rule="",
            )
    # create agent
    prompt = prompt_template.format_map(rules_to_prompt_str(rules))
    agent = create_agent(
        prompt=prompt,
        tools=[create_relevant_data_tool(app_id=app.id, ws_id=ws.id)],
        name="rule_engine",
        streaming=False,
    )
    # run agent
    kwargs_str = "\n".join(f"{key}: {value};" for key, value in kwargs.items())
    content = f"""
      workspace_id: {ws.id};
      app_name: {app.unique_name};
      directory_name: {dir.name};
      user_email: {user_email};
      {kwargs_str}
    """
    answer = agent.invoke(input={MEMORY_KEY: [HumanMessage(content=content)]})
    return answer
