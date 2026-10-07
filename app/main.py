import os
from typing import Literal
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from .db import make_engine, database_url, session_factory
from .models import Conversation, Message, AIAnalysis, KnowledgeEntry, AuditEvent, InternalNote, now
from .providers import AIProvider, AnalysisInput, digest, get_provider
from .operations import sla, metrics, OPERATORS, TRANSITIONS
class ConversationCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
class ConversationUpdate(BaseModel):
    status: Literal['New', 'In review', 'Resolved'] | None = None
    priority: Literal['Low', 'Medium', 'High'] | None = None
    assignee: str | None = Field(default=None, max_length=100)
class MessageCreate(BaseModel):
    role: Literal['user', 'assistant', 'system'] = 'user'
    content: str = Field(min_length=1, max_length=20000)
class KnowledgeCreate(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=20000)
def serialize(obj):
    data = {column.name: getattr(obj, column.name) for column in obj.__table__.columns}
    if isinstance(obj, Conversation):
        data.update(sla(obj))
    return data
def create_app(url: str | None = None, provider: AIProvider | None = None):
    app = FastAPI(title='HELIXPRIMUS', version='0.3.0')
    app.state.engine = make_engine(url or database_url())
    factory = session_factory(app.state.engine)
    ai = provider or get_provider(os.getenv('AI_PROVIDER', 'mock'))
    def db():
        with factory() as session:
            yield session
    def conversation(session, cid):
        item = session.get(Conversation, cid)
        if item is None:
            raise HTTPException(404, 'Conversation not found')
        return item
    def audit(session, action, item):
        session.add(AuditEvent(action=action, entity_id=item.id, details={'conversation_id': getattr(item, 'conversation_id', item.id)}))
    @app.get('/health')
    def health():
        return {'status': 'ok', 'ai_provider': ai.name}
    @app.post('/api/v1/conversations', status_code=201)
    def create_conversation(body: ConversationCreate, session: Session = Depends(db)):
        item = Conversation(title=body.title)
        session.add(item)
        session.flush()
        audit(session, 'conversation.created', item)
        session.commit()
        return serialize(item)
    @app.get('/api/v1/conversations')
    def conversations(session: Session = Depends(db), limit: int = 50, offset: int = 0, status: Literal['New', 'In review', 'Resolved'] | None = None, priority: Literal['Low', 'Medium', 'High'] | None = None, assignee: str | None = None, q: str = '', sla_state: Literal['On track', 'At risk', 'Overdue'] | None = None):
        if not 1 <= limit <= 100 or offset < 0:
            raise HTTPException(422, 'Invalid pagination')
        query = select(Conversation)
        for column, value in ((Conversation.status, status), (Conversation.priority, priority), (Conversation.assignee, assignee)):
            if value is not None:
                query = query.where(column == value)
        if q:
            pattern = '%' + q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
            query = query.where(or_(Conversation.title.ilike(pattern, escape='\\'), Conversation.id.in_(select(Message.conversation_id).where(Message.content.ilike(pattern, escape='\\')))))
        items = [serialize(x) for x in session.scalars(query.order_by(Conversation.updated_at.desc(), Conversation.id))]
        if sla_state:
            items = [x for x in items if not x['sla_closed'] and x['sla_state'] == sla_state]
        return items[offset:offset+limit]
    @app.patch('/api/v1/conversations/{cid}')
    def update_conversation(cid: str, body: ConversationUpdate, session: Session = Depends(db)):
        item = conversation(session, cid)
        changes = body.model_dump(exclude_unset=True)
        if any(value is None for value in changes.values()):
            raise HTTPException(422, 'Fields cannot be null')
        if 'assignee' in changes and changes['assignee'] not in OPERATORS:
            raise HTTPException(422, 'Choose a registered demo operator')
        if 'status' in changes and changes['status'] != item.status and changes['status'] not in TRANSITIONS[item.status]:
            raise HTTPException(409, 'Allowed transitions: New → In review → Resolved; Reopen → In review')
        for key, value in changes.items():
            if getattr(item, key) != value:
                session.add(AuditEvent(action='conversation.' + key + '.changed', entity_id=cid, details={'conversation_id': cid, 'before': getattr(item, key), 'after': value}))
                setattr(item, key, value)
                if key == 'status':
                    item.resolved_at = now() if value == 'Resolved' else None
        item.updated_at = now()
        session.commit()
        return serialize(item)
    @app.get('/api/v1/dashboard')
    def dashboard(session: Session = Depends(db)):
        return metrics(session)
    @app.get('/api/v1/conversations/{cid}')
    def get_conversation(cid: str, session: Session = Depends(db)):
        return serialize(conversation(session, cid))
    class NoteCreate(BaseModel):
        content: str = Field(min_length=1, max_length=5000)
        author: Literal['Alex Morgan', 'Sam Lee'] = 'Alex Morgan'
    @app.post('/api/v1/conversations/{cid}/notes', status_code=201)
    def add_note(cid: str, body: NoteCreate, session: Session = Depends(db)):
        conv = conversation(session, cid)
        if not body.content.strip():
            raise HTTPException(422, 'Note cannot be blank')
        item = InternalNote(conversation_id=cid, **body.model_dump())
        session.add(item)
        session.flush()
        conv.updated_at = now()
        session.add(AuditEvent(action='note.created', entity_id=item.id, details={'conversation_id': cid, 'author': body.author, 'content': body.content, 'internal': True}))
        session.commit()
        return serialize(item)
    @app.get('/api/v1/conversations/{cid}/notes')
    def notes(cid: str, session: Session = Depends(db)):
        conversation(session, cid)
        return [serialize(x) for x in session.scalars(select(InternalNote).where(InternalNote.conversation_id == cid).order_by(InternalNote.created_at, InternalNote.id))]
    @app.get('/api/v1/conversations/{cid}/timeline')
    def timeline(cid: str, session: Session = Depends(db), limit: int = 100):
        conversation(session, cid)
        if not 1 <= limit <= 100:
            raise HTTPException(422, 'Invalid limit')
        query = select(AuditEvent).where(or_(AuditEvent.entity_id == cid, AuditEvent.details['conversation_id'].as_string() == cid))
        return [serialize(x) for x in session.scalars(query.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).limit(limit))]
    @app.get('/api/v1/operators')
    def operators():
        return list(OPERATORS)
    @app.post('/api/v1/conversations/{cid}/messages', status_code=201)
    def add_message(cid: str, body: MessageCreate, session: Session = Depends(db)):
        conv = conversation(session, cid)
        conv.updated_at = now()
        item = Message(conversation_id=cid, **body.model_dump())
        session.add(item)
        session.flush()
        audit(session, 'message.created', item)
        session.commit()
        return serialize(item)
    @app.get('/api/v1/conversations/{cid}/messages')
    def messages(cid: str, session: Session = Depends(db)):
        conversation(session, cid)
        return [serialize(x) for x in session.scalars(select(Message).where(Message.conversation_id == cid).order_by(Message.created_at, Message.id))]
    @app.post('/api/v1/conversations/{cid}/analyses', status_code=201)
    def analyze(cid: str, session: Session = Depends(db)):
        conv = conversation(session, cid)
        msgs = session.scalars(select(Message).where(Message.conversation_id == cid).order_by(Message.created_at, Message.id)).all()
        if not msgs:
            raise HTTPException(409, 'Conversation has no messages')
        kb = session.scalars(select(KnowledgeEntry).order_by(KnowledgeEntry.key)).all()
        data = AnalysisInput(tuple((m.role, m.content) for m in msgs), tuple((k.key, k.content) for k in kb))
        try:
            result = ai.analyze(data)
        except Exception as exc:
            raise HTTPException(502, 'AI provider failed') from exc
        new_priority = result.get('priority', 'Medium')
        if conv.priority != new_priority:
            session.add(AuditEvent(action='conversation.priority.changed', entity_id=cid, details={'conversation_id': cid, 'before': conv.priority, 'after': new_priority, 'source': 'analysis'}))
        conv.priority = new_priority
        conv.updated_at = now()
        item = AIAnalysis(conversation_id=cid, provider=ai.name, provider_version=ai.version, input_digest=digest(data), result=result)
        session.add(item)
        session.flush()
        audit(session, 'analysis.created', item)
        session.commit()
        return serialize(item)
    @app.get('/api/v1/conversations/{cid}/analyses')
    def analyses(cid: str, session: Session = Depends(db)):
        conversation(session, cid)
        return [serialize(x) for x in session.scalars(select(AIAnalysis).where(AIAnalysis.conversation_id == cid).order_by(AIAnalysis.created_at, AIAnalysis.id))]
    @app.post('/api/v1/knowledge', status_code=201)
    def add_knowledge(body: KnowledgeCreate, session: Session = Depends(db)):
        if session.scalar(select(KnowledgeEntry).where(KnowledgeEntry.key == body.key)):
            raise HTTPException(409, 'Knowledge key already exists')
        item = KnowledgeEntry(**body.model_dump())
        session.add(item)
        session.flush()
        audit(session, 'knowledge.created', item)
        session.commit()
        return serialize(item)
    @app.get('/api/v1/knowledge')
    def knowledge(session: Session = Depends(db)):
        return [serialize(x) for x in session.scalars(select(KnowledgeEntry).order_by(KnowledgeEntry.key))]
    @app.get('/api/v1/audit')
    def events(session: Session = Depends(db), limit: int = 50, conversation_id: str | None = None, action: str | None = None):
        if not 1 <= limit <= 100:
            raise HTTPException(422, 'Invalid limit')
        query = select(AuditEvent)
        if conversation_id:
            query = query.where(or_(AuditEvent.entity_id == conversation_id, AuditEvent.details['conversation_id'].as_string() == conversation_id))
        if action:
            query = query.where(AuditEvent.action == action)
        return list(reversed([serialize(x) for x in session.scalars(query.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).limit(limit))]))
    @app.post('/api/v1/demo/m3')
    @app.post('/api/v1/demo/m2')
    def m2_demo(session: Session = Depends(db)):
        from .dataset import seed
        seed(session)
        session.commit()
        return {'status': 'seeded'}
    @app.post('/api/v1/demo/order-5841')
    def demo(session: Session = Depends(db)):
        item = session.scalar(select(Conversation).where(Conversation.external_reference == 'demo:order:5841'))
        if item:
            return serialize(item)
        if not session.scalar(select(KnowledgeEntry).where(KnowledgeEntry.key == 'shipping-delay')):
            entry = KnowledgeEntry(key='shipping-delay', title='Delivery delays', content='Check carrier status before promising a delivery date. Escalate unresolved delays to a human.')
            session.add(entry)
            session.flush()
            audit(session, 'knowledge.created', entry)
        item = Conversation(title='Order #5841 delivery delay', external_reference='demo:order:5841')
        session.add(item)
        session.flush()
        message = Message(conversation_id=item.id, role='user', content='My order #5841 is delayed. Can you check the delivery status?')
        session.add(message)
        session.flush()
        audit(session, 'message.created', message)
        audit(session, 'demo.created', item)
        session.commit()
        return serialize(item)
    @app.post('/api/v1/demo/billing-5841')
    def billing_demo(session: Session = Depends(db)):
        item = session.scalar(select(Conversation).where(Conversation.external_reference == 'demo:billing:5841'))
        if item:
            return serialize(item)
        if not session.scalar(select(KnowledgeEntry).where(KnowledgeEntry.key == 'refund-policy-3.2')):
            entry = KnowledgeEntry(key='refund-policy-3.2', title='Refund Policy §3.2', content='Duplicate payments: verify both transactions before issuing a refund. Confirmed duplicate charges are refunded to the original payment method. Never promise a refund before verification.')
            session.add(entry)
            session.flush()
            audit(session, 'knowledge.created', entry)
        item = Conversation(title='Duplicate payment · Order #5841', external_reference='demo:billing:5841')
        session.add(item)
        session.flush()
        session.add(Message(conversation_id=item.id, role='user', content='I was charged twice for order #5841. Can you refund the duplicate payment?'))
        audit(session, 'demo.created', item)
        session.commit()
        return serialize(item)
    class ReplyAction(BaseModel):
        action: Literal['edit', 'approve', 'mock-send']
        content: str = Field(min_length=1, max_length=20000)
    @app.post('/api/v1/conversations/{cid}/analyses/{aid}/reply')
    def reply_action(cid: str, aid: str, body: ReplyAction, session: Session = Depends(db)):
        conv = conversation(session, cid)
        item = session.get(AIAnalysis, aid)
        if item is None or item.conversation_id != cid:
            raise HTTPException(404, 'Analysis not found')
        result = dict(item.result)
        def reject_send(reason):
            if body.action == 'mock-send':
                session.add(AuditEvent(action='reply.mock-send.rejected', entity_id=item.id, details={'conversation_id': cid, 'reason': reason}))
                session.commit()
            raise HTTPException(409, reason)
        if result.get('reply_status') == 'sent':
            reject_send('Reply already sent')
        if body.action == 'mock-send' and (result.get('reply_status') != 'approved' or result.get('reply_content') != body.content):
            reject_send('Approve the exact reply before sending')
        if not body.content.strip():
            raise HTTPException(422, 'Reply cannot be blank')
        result.update(reply_content=body.content, reply_status={'edit': 'draft', 'approve': 'approved', 'mock-send': 'sent'}[body.action])
        item.result = result
        conv.updated_at = now()
        session.add(AuditEvent(action='reply.' + body.action, entity_id=item.id, details={'conversation_id': cid, 'content': body.content, 'synthetic': True}))
        if body.action == 'mock-send':
            session.add(Message(conversation_id=cid, role='assistant', content=body.content))
        session.commit()
        return serialize(item)
    return app
app = create_app()
