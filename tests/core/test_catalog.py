from docai.core import catalog
from docai.contracts.messages import QUEUES, TOPIC


def test_counts_match_the_spec():
    assert len(catalog.jobs()) == 13 and len(catalog.apps()) == 8


def test_every_queue_has_exactly_one_consumer_and_every_target_exists():
    consumers = [c.consumes_queue for c in catalog.COMPONENTS if c.consumes_queue]
    assert sorted(consumers) == sorted(QUEUES), "each queue needs one consumer"
    for c in catalog.COMPONENTS:
        for dest in c.sends:
            assert dest in QUEUES or dest == TOPIC, (c.name, dest)


def test_review_app_keeps_a_replica_for_the_outbox_relay():
    assert catalog.BY_NAME["app-review"].min_replicas == 1


def test_identity_rights_follow_the_least_privilege_table():
    ocr = catalog.role_assignments(catalog.BY_NAME["job-ocr-online"])
    assert ("Azure Service Bus Data Receiver", "queue", "q-ocr-online") in ocr
    assert ("Azure Service Bus Data Sender", "queue", "q-reconcile") in ocr
    assert not any(r[1] == "queue" and r[2] == "q-intake" for r in ocr)
    watchdog = catalog.role_assignments(catalog.BY_NAME["job-watchdog"])
    assert sum(1 for r in watchdog if r[0].endswith("Receiver")) == len(QUEUES)


def test_every_queue_has_a_sender():
    sent = {d for c in catalog.COMPONENTS for d in c.sends}
    assert set(QUEUES) <= sent, set(QUEUES) - sent


# ---- drift guard: what a module's code uses must be granted to its identity (the tests run as an administrator and cannot see this)
import re
from pathlib import Path

MODULES = Path(__file__).resolve().parents[2] / "src" / "docai" / "modules"


def _source(c):
    return (MODULES / f"{c.module}.py").read_text()


def test_every_component_that_uses_search_sql_or_storage_has_the_matching_grant():
    for c in catalog.COMPONENTS:
        src = _source(c)
        if re.search(r"ctx\.search\b", src):
            assert c.search, f"{c.name} uses AI Search but has no Search role"
        if "ctx.ops" in src or "review.relay_outbox" in src:
            assert c.sql_role, f"{c.name} uses SQL but has no SQL role"
        for container in re.findall(r'"(raw|extracted|curated|staging|quarantine)"', src):
            assert container in c.containers, f"{c.name} touches the {container} container but has no role on it"
        if "ctx.search.upload" in src or "ctx.search.merge" in src or "ctx.search.delete" in src:
            assert c.search == "contributor", f"{c.name} writes to AI Search but is only a reader"
        if re.search(r"send\(|ctx\.queue\.send", src):
            assert c.sends, f"{c.name} sends messages but may send to nothing"
        if re.search(r"ctx\.safety|ctx\.chat|ctx\.vision|ctx\.embedder|ctx\.ocr|ctx\.agent", src):
            assert c.foundry, f"{c.name} calls an AI model but has no AI Services role"


def test_the_demand_and_registry_roles_have_what_the_adapter_calls():
    assert catalog.BY_NAME["app-retrieval"].sql_role == catalog.BY_NAME["app-verifier"].sql_role == "r_lookup"
