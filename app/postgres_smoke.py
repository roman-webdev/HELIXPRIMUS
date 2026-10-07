"""Run against an explicitly configured, disposable local PostgreSQL database."""
import os
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url
from .db import database_url
from .demo import reset_demo
from .main import create_app


def main():
    url = make_url(database_url())
    if (url.get_backend_name() != 'postgresql' or url.host not in ('localhost', '127.0.0.1', '::1')
            or not url.database or not url.database.endswith('_smoke')):
        raise SystemExit('Set DATABASE_URL to a disposable loopback PostgreSQL database ending in _smoke; stop backend first.')
    os.environ['AI_PROVIDER'] = 'mock'
    config = Config('alembic.ini')
    command.upgrade(config, 'head')
    app = create_app()
    try:
        reset_demo(app.state.engine)
        with TestClient(app) as client:
            def request(method, path, **kwargs):
                response = client.request(method, '/api/v1/' + path, **kwargs)
                response.raise_for_status()
                return response.json()

            assert client.get('/health').status_code == 200
            request('POST', 'demo/m2')
            request('POST', 'demo/m2')  # Seeding is idempotent.
            items = request('GET', 'conversations')
            assert len([c for c in items if (c['external_reference'] or '').startswith('demo:')]) == 6
            assert len(request('GET', 'knowledge')) >= 4
            billing = next(c for c in items if c['external_reference'] == 'demo:billing:5841')
            cid = billing['id']
            base = f'conversations/{cid}'
            assert request('GET', 'conversations', params={'q': 'CHARGED TWICE', 'status': 'New', 'priority': 'High', 'assignee': 'Alex Morgan'})[0]['id'] == cid
            assert request('GET', 'conversations', params={'q': '%_nonexistent'}) == []
            expected = {'demo:billing:5841': 'refund-policy-3.2', 'demo:order:5841': 'shipping-delay',
                        'demo:access:5842': 'account-access', 'demo:cancel:5843': 'cancellation-refund'}
            for item in items:
                if item['external_reference'] in expected:
                    a = request('POST', f"conversations/{item['id']}/analyses")
                    assert a['result']['knowledge_citations'] == [expected[item['external_reference']]]
            a = request('POST', base + '/analyses')
            reply_path = base + f"/analyses/{a['id']}/reply"
            content = 'PostgreSQL smoke #5841: verify both transactions before confirming any refund.'
            assert client.post('/api/v1/' + reply_path, json={'action': 'mock-send', 'content': content}).status_code == 409
            sends_before = request('GET', 'dashboard')['mock_sends']
            for action, status in [('edit', 'draft'), ('approve', 'approved'), ('mock-send', 'sent')]:
                assert request('POST', reply_path, json={'action': action, 'content': content})['result']['reply_status'] == status
            assert request('GET', base + '/messages')[-1]['content'] == content
            assert request('GET', base + '/analyses')[-1]['result']['reply_status'] == 'sent'
            assert client.post('/api/v1/' + reply_path, json={'action': 'mock-send', 'content': content}).status_code == 409
            for action in ('reply.edit', 'reply.approve', 'reply.mock-send'):
                events = request('GET', 'audit', params={'conversation_id': cid, 'action': action})
                assert any(e['details']['content'] == content for e in events)
            request('PATCH', base, json={'status': 'In review'})
            request('PATCH', base, json={'status': 'Resolved', 'assignee': 'Sam Lee', 'priority': 'Low'})
            assert request('GET', base)['status'] == 'Resolved'
            dashboard = request('GET', 'dashboard')
            assert dashboard['mock_sends'] == sends_before + 1
            assert dashboard['resolved'] >= 3 and dashboard['average_resolution_minutes'] is not None
            request('PATCH', base, json={'status': 'In review'})
            assert request('GET', base)['resolved_at'] is None
            request('POST', base+'/notes', json={'content': 'M3 PostgreSQL handoff', 'author': 'Sam Lee'})
            assert request('GET', base+'/notes')[0]['content'] == 'M3 PostgreSQL handoff'
            assert any(e['action']=='note.created' for e in request('GET', base+'/timeline'))
            assert a['result']['confidence']['intent'] > .9
            assert a['result']['explanations']['kb_match']
            assert dashboard['average_first_response_minutes'] is not None
            assert dashboard['mock_send_success_rate'] is not None
            assert dashboard['sla_distribution'] and len(dashboard['trend']) == 7
            assert client.patch('/api/v1/'+base,json={'status':'New'}).status_code == 409
        fresh_app = create_app()
        try:
            with TestClient(fresh_app) as fresh:
                assert fresh.get('/api/v1/' + base + '/messages').json()[-1]['content'] == content
                assert fresh.get('/api/v1/' + base + '/notes').json()[0]['content'] == 'M3 PostgreSQL handoff'
        finally:
            fresh_app.state.engine.dispose()
        command.check(config)
        print('PostgreSQL M3 smoke PASS: filters/search, four AI/KB scenarios, approval gating, persisted send, Dashboard, Audit, status transitions, confidence/explanations, SLA analytics, notes/timeline, reload persistence, schema drift.')
    finally:
        app.state.engine.dispose()


if __name__ == '__main__':
    main()
