import pytest

from fastapi.testclient import TestClient

from alembic.config import Config

from alembic import command

from sqlalchemy import inspect

from app.main import create_app

from app.providers import MockAIProvider, AnalysisInput



@pytest.fixture

def client(tmp_path, monkeypatch):

    url = 'sqlite:///' + (tmp_path / 'test.db').as_posix()

    monkeypatch.setenv('DATABASE_URL', url)

    command.upgrade(Config('alembic.ini'), 'head')

    app = create_app(url)

    with TestClient(app) as client:

        yield client

    app.state.engine.dispose()



def test_demo_analysis_deterministic_and_persisted(client):

    assert client.get('/health').status_code == 200

    demo = client.post('/api/v1/demo/order-5841').json()

    cid = demo['id']

    assert client.post('/api/v1/demo/order-5841').json()['id'] == cid

    assert len(client.get(f'/api/v1/conversations/{cid}/messages').json()) == 1

    a = client.post(f'/api/v1/conversations/{cid}/analyses').json()

    b = client.post(f'/api/v1/conversations/{cid}/analyses').json()

    assert a['result'] == b['result']

    assert a['input_digest'] == b['input_digest']

    assert a['result']['order_numbers'] == ['5841']

    assert a['result']['intent'] == 'order_delay'

    assert a['result']['knowledge_citations'] == ['shipping-delay']

    assert len(client.get(f'/api/v1/conversations/{cid}/analyses').json()) == 2

    assert any(e['action'] == 'analysis.created' for e in client.get('/api/v1/audit').json())



def test_crud_and_validation(client):

    cid = client.post('/api/v1/conversations', json={'title': 'Support'}).json()['id']

    assert client.get(f'/api/v1/conversations/{cid}').status_code == 200

    assert client.post(f'/api/v1/conversations/{cid}/analyses').status_code == 409

    assert client.post(f'/api/v1/conversations/{cid}/messages', json={'role': 'invalid', 'content': 'x'}).status_code == 422

    assert client.post(f'/api/v1/conversations/{cid}/messages', json={'content': ''}).status_code == 422

    assert client.post(f'/api/v1/conversations/{cid}/messages', json={'content': 'Hello'}).status_code == 201

    assert client.post(f'/api/v1/conversations/{cid}/analyses').json()['result']['intent'] == 'general_inquiry'

    assert client.get('/api/v1/conversations?limit=101').status_code == 422

    assert client.get('/api/v1/conversations/missing/messages').status_code == 404

    assert client.post('/api/v1/conversations/missing/analyses').status_code == 404

    assert client.post('/api/v1/conversations/missing/messages', json={'content': 'x'}).status_code == 404

    assert len(client.get('/api/v1/conversations').json()) == 1



def test_knowledge_duplicate(client):

    body = {'key': 'policy', 'title': 'Policy', 'content': 'Review'}

    assert client.post('/api/v1/knowledge', json=body).status_code == 201

    assert client.post('/api/v1/knowledge', json=body).status_code == 409

    assert len(client.get('/api/v1/knowledge').json()) == 1



def test_input_changes_digest(client):

    cid = client.post('/api/v1/demo/order-5841').json()['id']

    a = client.post(f'/api/v1/conversations/{cid}/analyses').json()

    client.post(f'/api/v1/conversations/{cid}/messages', json={'content': 'Update please'})

    b = client.post(f'/api/v1/conversations/{cid}/analyses').json()

    assert a['input_digest'] != b['input_digest']



def test_provider_failure_is_atomic(client):

    class Broken:

        name, version = 'broken', '1'

        def analyze(self, data):

            raise RuntimeError('secret')

    app = create_app(str(client.app.state.engine.url), Broken())

    cid = client.post('/api/v1/demo/order-5841').json()['id']

    with TestClient(app) as other:

        response = other.post(f'/api/v1/conversations/{cid}/analyses')

        assert response.status_code == 502

        assert 'secret' not in response.text

    assert client.get(f'/api/v1/conversations/{cid}/analyses').json() == []

    app.state.engine.dispose()



def test_provider_pure():

    provider = MockAIProvider()

    data = AnalysisInput((('user', 'Order #5841 delayed'),), ())

    assert provider.analyze(data) == provider.analyze(data)

    assert provider.analyze(data)['knowledge_citations'] == []



def test_migration_roundtrip(client):

    config = Config('alembic.ini')

    command.check(config)

    command.downgrade(config, 'base')

    assert 'conversations' not in inspect(client.app.state.engine).get_table_names()

    command.upgrade(config, 'head')

    assert 'conversations' in inspect(client.app.state.engine).get_table_names()



def test_database_foreign_keys(client):

    from sqlalchemy.orm import Session

    from sqlalchemy.exc import IntegrityError

    from app.models import Message

    with Session(client.app.state.engine) as session:

        session.add(Message(conversation_id='missing', role='user', content='Hello'))

        with pytest.raises(IntegrityError):

            session.commit()



def test_postgresql_schema_compiles():

    from sqlalchemy.schema import CreateTable

    from sqlalchemy.dialects import postgresql

    from app.db import Base

    for table in Base.metadata.sorted_tables:

        assert 'CREATE TABLE' in str(CreateTable(table).compile(dialect=postgresql.dialect()))





def test_billing_reply_lifecycle(client):

    cid = client.post('/api/v1/demo/billing-5841').json()['id']

    assert client.post('/api/v1/demo/billing-5841').json()['id'] == cid

    a = client.post(f'/api/v1/conversations/{cid}/analyses').json()

    assert a['result']['intent'] == 'Billing issue'

    assert a['result']['priority'] == 'High'

    assert a['result']['sentiment'] == 'Negative'

    assert a['result']['knowledge_citations'] == ['refund-policy-3.2']

    url = f"/api/v1/conversations/{cid}/analyses/{a['id']}/reply"

    def action(name, content='Reviewed synthetic reply'):

        return client.post(url, json={'action': name, 'content': content})

    assert action('mock-send').status_code == 409

    assert action('edit').status_code == 200

    assert action('approve').status_code == 200

    assert action('mock-send', 'Changed after approval').status_code == 409

    assert action('edit').json()['result']['reply_status'] == 'draft'

    assert action('mock-send').status_code == 409

    assert action('approve').status_code == 200

    assert action('mock-send').json()['result']['reply_status'] == 'sent'

    assert action('mock-send').status_code == 409

    assert len(client.get(f'/api/v1/conversations/{cid}/messages').json()) == 2

    events = client.get('/api/v1/audit').json()

    assert any(e['action'] == 'reply.mock-send' and e['details']['synthetic'] for e in events)


def test_reset_demo_is_scoped_and_seed_is_repeatable(client):
    from app.demo import reset_demo
    other = client.post('/api/v1/conversations', json={'title': 'Keep me'}).json()['id']
    client.post(f'/api/v1/conversations/{other}/messages', json={'content': 'Keep message'})
    cid = client.post('/api/v1/demo/billing-5841').json()['id']
    a = client.post(f'/api/v1/conversations/{cid}/analyses').json()
    reply = f"/api/v1/conversations/{cid}/analyses/{a['id']}/reply"
    client.post(reply, json={'action': 'approve', 'content': 'Synthetic reply'})
    client.post(reply, json={'action': 'mock-send', 'content': 'Synthetic reply'})
    reset_demo(client.app.state.engine)
    reset_demo(client.app.state.engine)
    assert client.get(f'/api/v1/conversations/{cid}').status_code == 404
    assert len(client.get(f'/api/v1/conversations/{other}/messages').json()) == 1
    assert not any(e['entity_id'] in (cid, a['id']) or e['details'].get('conversation_id') == cid for e in client.get('/api/v1/audit').json())
    for scenario in ('order-5841', 'billing-5841'):
        demo = client.post('/api/v1/demo/' + scenario).json()
        assert client.post('/api/v1/demo/' + scenario).json()['id'] == demo['id']
        assert len(client.get(f"/api/v1/conversations/{demo['id']}/messages").json()) == 1
        assert client.get(f"/api/v1/conversations/{demo['id']}/analyses").json() == []


def test_m2_dataset_filters_dashboard_and_audit(client):
    from app.demo import reset_demo
    other = client.post('/api/v1/conversations', json={'title': 'Unrelated record'}).json()['id']
    assert client.post('/api/v1/demo/m2').status_code == 200
    assert client.post('/api/v1/demo/m2').status_code == 200
    items = client.get('/api/v1/conversations').json()
    assert len(items) == 7
    assert len(client.get('/api/v1/knowledge').json()) == 4
    for row in items:
        if not row['external_reference']:
            continue
        result = client.post(f"/api/v1/conversations/{row['id']}/analyses").json()['result']
        assert result['priority'] and result['sentiment'] and result['summary'] and result['entities']
        assert len(result['knowledge_citations']) == 1
    assert len(client.get('/api/v1/conversations?status=Resolved').json()) == 2
    assert len(client.get('/api/v1/conversations?priority=High').json()) == 3
    assert len(client.get('/api/v1/conversations?assignee=Sam%20Lee').json()) == 3
    assert len(client.get('/api/v1/conversations?q=reset').json()) == 2
    assert client.get('/api/v1/conversations?q=%25').json() == []
    assert client.get('/api/v1/conversations?status=invalid').status_code == 422
    cid = next(c['id'] for c in items if c['external_reference'] == 'demo:billing:5841')
    assert client.patch(f'/api/v1/conversations/{cid}', json={'status': 'In review'}).status_code == 200
    assert client.patch(f'/api/v1/conversations/{cid}', json={'status': 'Resolved', 'assignee': 'Sam Lee'}).status_code == 200
    assert client.patch(f'/api/v1/conversations/{cid}', json={'status': None}).status_code == 422
    assert client.patch('/api/v1/conversations/missing', json={'status': 'New'}).status_code == 404
    events = client.get(f'/api/v1/audit?conversation_id={cid}&action=conversation.status.changed').json()
    assert len(events) == 2 and events[-1]['details']['after'] == 'Resolved'
    d = client.get('/api/v1/dashboard').json()
    assert (d['total'], d['open'], d['resolved']) == (7, 4, 3)
    assert sum(d['priority_distribution'].values()) == 7
    assert sum(d['intent_distribution'].values()) == 7
    assert d['average_resolution_minutes'] is not None
    client.patch(f'/api/v1/conversations/{cid}', json={'status': 'In review'})
    assert client.get(f'/api/v1/conversations/{cid}').json()['resolved_at'] is None
    reset_demo(client.app.state.engine)
    assert [c['id'] for c in client.get('/api/v1/conversations').json()] == [other]
    client.post('/api/v1/demo/m2')
    assert len(client.get('/api/v1/conversations').json()) == 7

@pytest.mark.parametrize('text,intent,key', [
    ('Charged twice for #5841', 'Billing issue', 'refund-policy-3.2'),
    ('Order #99 is delayed', 'order_delay', 'shipping-delay'),
    ('Cannot login after password reset', 'account_access', 'account-access'),
    ('Cancel order #42 and refund', 'cancellation_refund', 'cancellation-refund'),
])
def test_m2_matching(text, intent, key):
    provider = MockAIProvider()
    data = AnalysisInput((('user', text),), ((key, 'Synthetic policy'), ('unrelated', 'Unrelated policy')))
    result = provider.analyze(data)
    assert result['intent'] == intent and result['knowledge_citations'] == [key]
    assert result == provider.analyze(data)
    assert provider.analyze(AnalysisInput(data.messages, ()))['knowledge_citations'] == []


def test_dashboard_counts_sends_without_audit_window(client):
    from sqlalchemy.orm import Session
    from app.models import AuditEvent
    cid = client.post('/api/v1/demo/billing-5841').json()['id']
    a = client.post(f'/api/v1/conversations/{cid}/analyses').json()
    url = f"/api/v1/conversations/{cid}/analyses/{a['id']}/reply"
    client.post(url, json={'action': 'approve', 'content': 'Reviewed response'})
    client.post(url, json={'action': 'mock-send', 'content': 'Reviewed response'})
    with Session(client.app.state.engine) as session:
        session.add_all([AuditEvent(action='test.activity', entity_id=cid) for _ in range(110)])
        session.commit()
    assert client.get('/api/v1/dashboard').json()['mock_sends'] == 1
    assert len(client.get('/api/v1/audit?limit=100').json()) == 100
    events = client.get(f'/api/v1/audit?conversation_id={cid}&action=reply.mock-send').json()
    assert len(events) == 1


def test_m3_transitions_reassignment_notes_and_reload(client):
    cid = client.post('/api/v1/demo/billing-5841').json()['id']
    base = f'/api/v1/conversations/{cid}'
    assert client.patch(base, json={'status': 'Resolved', 'assignee': 'Sam Lee'}).status_code == 409
    assert client.get(base).json()['assignee'] == 'Unassigned'
    assert client.patch(base, json={'assignee': 'Unknown'}).status_code == 422
    assert client.patch(base, json={'status': 'In review', 'assignee': 'Alex Morgan'}).status_code == 200
    assert client.patch(base, json={'assignee': 'Sam Lee'}).status_code == 200
    note = 'Verify transaction IDs before offering a refund. ' * 50
    assert client.post(base+'/notes', json={'content': '   '}).status_code == 422
    assert client.post(base+'/notes', json={'content': note, 'author': 'Sam Lee'}).status_code == 201
    assert len(client.get(base+'/messages').json()) == 1
    assert client.patch(base, json={'status': 'Resolved'}).status_code == 200
    assert client.patch(base, json={'status': 'New'}).status_code == 409
    assert client.patch(base, json={'status': 'In review'}).json()['resolved_at'] is None
    fresh = create_app(str(client.app.state.engine.url))
    try:
        with TestClient(fresh) as other:
            assert other.get(base).json()['assignee'] == 'Sam Lee'
            assert other.get(base+'/notes').json()[0]['content'] == note
            events = other.get(base+'/timeline').json()
            assert any(e['action'] == 'note.created' and e['details']['author'] == 'Sam Lee' for e in events)
            assert any(e['action'] == 'conversation.assignee.changed' and e['details']['before'] == 'Alex Morgan' for e in events)
            assert other.get(base+'/timeline?limit=101').status_code == 422
    finally:
        fresh.state.engine.dispose()

def test_m3_confidence_evidence_and_missing_policy(client):
    client.post('/api/v1/demo/m3')
    cid = next(c['id'] for c in client.get('/api/v1/conversations').json() if c['external_reference']=='demo:billing:5841')
    result = client.post(f'/api/v1/conversations/{cid}/analyses').json()['result']
    assert set(result['confidence']) == {'intent','priority','sentiment','kb_match'}
    assert all(0 <= v <= 1 for v in result['confidence'].values())
    assert 'charged twice' in result['evidence']
    assert '5841' in result['explanations']['entities']
    assert 'refund-policy-3.2' in result['explanations']['kb_match']
    provider = MockAIProvider()
    data = AnalysisInput((('user','charged twice'),), ())
    assert provider.analyze(data)['confidence']['kb_match'] == 0
    assert provider.analyze(AnalysisInput((('user','hello'),),()))['confidence']['intent'] < result['confidence']['intent']

def test_m3_sla_boundaries_priority_and_reopen(client):
    from datetime import datetime, timedelta, timezone
    from app.operations import sla
    from app.models import Conversation
    at = datetime(2026,10,6,12,tzinfo=timezone.utc)
    c = Conversation(status='New', priority='High', created_at=at)
    assert sla(c,at+timedelta(minutes=95))['sla_state']=='On track'
    assert sla(c,at+timedelta(minutes=96))['sla_state']=='At risk'
    assert sla(c,at+timedelta(minutes=120))['sla_state']=='At risk'
    assert sla(c,at+timedelta(minutes=121))['sla_state']=='Overdue'
    c.status='Resolved'; c.resolved_at=at+timedelta(minutes=100)
    assert sla(c,at+timedelta(days=1))['sla_state']=='On track'
    c.status='In review';c.resolved_at=None
    assert sla(c,at+timedelta(days=1))['sla_state']=='Overdue'
    c.priority='Low'
    assert sla(c,at+timedelta(minutes=121))['sla_state']=='On track'
    client.post('/api/v1/demo/m3')
    for state in ('On track','At risk','Overdue'):
        rows=client.get('/api/v1/conversations',params={'sla_state':state}).json()
        assert rows and all(c['sla_state']==state and c['status']!='Resolved' for c in rows)
    assert client.get('/api/v1/conversations?sla_state=invalid').status_code==422

def test_m3_metrics_exact_durations_rates_and_backlog(client):
    from datetime import timedelta
    from sqlalchemy.orm import Session
    from app.models import Conversation, Message, now
    assert client.get('/api/v1/dashboard').json()['approval_rate'] is None
    cid=client.post('/api/v1/demo/billing-5841').json()['id']
    base=f'/api/v1/conversations/{cid}'
    a=client.post(base+'/analyses').json()
    reply=base+f"/analyses/{a['id']}/reply"
    assert client.post(reply,json={'action':'mock-send','content':'Reply'}).status_code==409
    for action in ('approve','mock-send'):
        assert client.post(reply,json={'action':action,'content':'Reply'}).status_code==200
    client.patch(base,json={'status':'In review'})
    client.patch(base,json={'status':'Resolved'})
    with Session(client.app.state.engine) as session:
        at=now()-timedelta(days=1)
        conv=session.get(Conversation,cid);conv.created_at=at;conv.resolved_at=at+timedelta(minutes=60)
        for m in session.query(Message).filter_by(conversation_id=cid,role='assistant'):
            m.created_at=at+timedelta(minutes=15)
        session.commit()
    d=client.get('/api/v1/dashboard').json()
    assert d['average_first_response_minutes']==15
    assert d['average_resolution_minutes']==60
    assert d['approval_rate']==100 and d['approval_denominator']==1
    assert d['mock_send_success_rate']==50 and d['mock_send_attempts']==2
    assert d['backlog_by_priority']=={} and d['sla_overdue']==0
    assert d['assignee_distribution']=={'Unassigned':1}
    assert len(d['trend'])==7 and sum(x['resolved'] for x in d['trend'])==1
    client.patch(base,json={'status':'In review'})
    d=client.get('/api/v1/dashboard').json()
    assert d['average_resolution_minutes'] is None and d['sla_overdue']==1

def test_m3_reset_clears_notes_and_preserves_other_notes(client):
    from app.demo import reset_demo
    client.post('/api/v1/demo/m3')
    other=client.post('/api/v1/conversations',json={'title':'Independent'}).json()['id']
    client.post(f'/api/v1/conversations/{other}/notes',json={'content':'Keep this'})
    reset_demo(client.app.state.engine)
    assert client.get(f'/api/v1/conversations/{other}/notes').json()[0]['content']=='Keep this'
    client.post('/api/v1/demo/m3')
    assert len(client.get('/api/v1/conversations').json())==7
