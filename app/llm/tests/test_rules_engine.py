import unittest

from sqlalchemy.engine import create_engine

from app.llm.tools.rule_engine.rule_engine_agent import get_rules, rules_to_prompt_str
from app.models import Rule, RuleTypes, ThenTypes
from app.models_stores import RuleStore
from app.models_stores_sql import RuleStoreSQL
from app.services import set_service_registry
from app.sql import SQLAlchemyTransactionContext


class TestWorkspaceStoreSQL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import injector

        # Set up a test engine, possibly an in-memory database
        cls.engine = create_engine("sqlite:///:memory:")
        cls.test_store = RuleStoreSQL()
        cls.test_store.create_tables(cls.engine)

        class ExtensionModule(injector.Module):
            def configure(self, binder):
                binder.bind(RuleStore, to=RuleStoreSQL, scope=injector.singleton)

        service_registry = injector.Injector([ExtensionModule()])
        set_service_registry(service_registry)

    def test_get_rules(self):
        app_id = "1"
        dir_id = "1"
        rule1when = "sensitivity lower than 2"
        rule3when = "user is from IT"
        rule5when = "app is active directory"
        rules = [
            Rule(
                id="1",
                workspace_id="1",
                created_by="foo",
                type=RuleTypes.auto_approve,
                when=rule1when,
                then=ThenTypes.approve,
            ),
            Rule(
                id="2",
                workspace_id="2",
                created_by="foo",
                type=RuleTypes.auto_approve,
                when="dsadsa",
                then=ThenTypes.approve,
            ),
            Rule(
                id="3",
                workspace_id="1",
                created_by="foo",
                type=RuleTypes.auto_approve,
                when=rule3when,
                then=ThenTypes.approve,
                application_ids=[app_id],
            ),
            Rule(
                id="4",
                workspace_id="1",
                created_by="foo",
                type=RuleTypes.auto_approve,
                when="dsadsa",
                then=ThenTypes.approve,
                application_ids=["foo"],
            ),
            Rule(
                id="5",
                workspace_id="1",
                created_by="foo",
                type=RuleTypes.auto_approve,
                when=rule5when,
                then=ThenTypes.deny,
                directory_ids=[dir_id],
            ),
            Rule(
                id="6",
                workspace_id="1",
                created_by="foo",
                type=RuleTypes.auto_approve,
                when="dsadsa",
                then=ThenTypes.deny,
                directory_ids=["foo"],
            ),
            Rule(
                id="7",
                workspace_id="1",
                created_by="foo",
                type=RuleTypes.auto_approve,
                when=rule1when,
                then=ThenTypes.approve,
                active=False,
            ),
        ]
        with SQLAlchemyTransactionContext(engine=self.engine).manage() as tx_context:
            for r in rules:
                self.test_store.insert(rule=r, tx_context=tx_context)

            rules = get_rules(
                ws_id="1", app_id=app_id, dir_id=dir_id, tx_context=tx_context
            )
            approve_rules = rules["approve_rules"]
            self.assertEqual(2, len(approve_rules))
            self.assertSetEqual(set(["1", "3"]), set([r.id for r in approve_rules]))
            deny_rules = rules["deny_rules"]
            self.assertEqual(1, len(deny_rules))
            self.assertSetEqual(set(["5"]), set([r.id for r in deny_rules]))

            rstr = rules_to_prompt_str(rules)
            expectedApproveStr = f"- {rule1when}\n- {rule3when}"
            expectedDenyStr = f"- {rule5when}"
            self.assertEqual(rstr["approve_rules"], expectedApproveStr)
            self.assertEqual(rstr["deny_rules"], expectedDenyStr)
