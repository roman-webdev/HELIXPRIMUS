"""Local M3 demo tools; run from the repository root."""
import argparse
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, or_
from sqlalchemy.orm import Session
from .main import create_app
from .models import Conversation, Message, AIAnalysis, InternalNote, AuditEvent
from .providers import MockAIProvider

from .dataset import REFERENCES

def reset_demo(engine):
    """Remove only the six explicitly owned synthetic conversations and their dependent audit data."""
    with Session(engine) as session, session.begin():
        ids = list(session.scalars(select(Conversation.id).where(Conversation.external_reference.in_(REFERENCES))))
        if not ids:
            return
        entity_ids = ids + list(session.scalars(select(Message.id).where(Message.conversation_id.in_(ids)))) + list(session.scalars(select(AIAnalysis.id).where(AIAnalysis.conversation_id.in_(ids))))
        session.execute(delete(AuditEvent).where(or_(AuditEvent.entity_id.in_(entity_ids), AuditEvent.details['conversation_id'].as_string().in_(ids))))
        session.execute(delete(AIAnalysis).where(AIAnalysis.conversation_id.in_(ids)))
        session.execute(delete(InternalNote).where(InternalNote.conversation_id.in_(ids)))
        session.execute(delete(Message).where(Message.conversation_id.in_(ids)))
        session.execute(delete(Conversation).where(Conversation.id.in_(ids)))

def main():
    parser = argparse.ArgumentParser(description='Seed or reset the scoped M3 synthetic dataset; existing policies are preserved.')
    parser.add_argument('action', choices=['seed', 'reset'])
    args = parser.parse_args()
    command.upgrade(Config('alembic.ini'), 'head')
    app = create_app(provider=MockAIProvider())
    try:
        if args.action == 'reset':
            reset_demo(app.state.engine)
        with TestClient(app) as client:
            for scenario in ('m2',):
                response = client.post('/api/v1/demo/' + scenario)
                response.raise_for_status()
                print('M3 synthetic dataset ready')
    finally:
        app.state.engine.dispose()

if __name__ == '__main__':
    main()
