"""Explicitly owned synthetic records. Never select demo scope by title."""

from sqlalchemy import select

from .models import Conversation, Message, KnowledgeEntry, AuditEvent, AIAnalysis, InternalNote

from .providers import MockAIProvider, AnalysisInput, digest

POLICIES = {

 'refund-policy-3.2': ('Refund Policy §3.2', 'Duplicate payments: verify both transactions before issuing a refund. Confirmed duplicates are refunded to the original method. Never promise a refund before verification.'),

 'shipping-delay': ('Delivery delays', 'Check carrier status before promising a delivery date. Escalate unresolved delays to a human.'),

 'account-access': ('Account access & identity', 'Use password reset first. Escalate continued lockout for identity verification. Never request passwords or verification codes.'),

 'cancellation-refund': ('Cancellation & return eligibility', 'Unshipped orders may be cancelled. Shipped orders require return review. Confirm eligibility before promising a refund.')

}

SCENARIOS = [

 ('demo:billing:5841', 'Duplicate payment · Order #5841', 'I was charged twice for order #5841. Can you refund the duplicate payment?', 'New', 'Alex Morgan'),

 ('demo:order:5841', 'Order #5841 delivery delay', 'My order #5841 is delayed. Can you check the delivery status?', 'In review', 'Sam Lee'),

 ('demo:access:5842', 'Account locked · Customer #5842', 'I cannot login. My account is locked after a password reset.', 'New', 'Unassigned'),

 ('demo:cancel:5843', 'Cancellation request · Order #5843', 'Please cancel order #5843 and review refund eligibility.', 'In review', 'Alex Morgan'),

 ('demo:delivery:5844', 'Delivery update · Order #5844', 'My order #5844 was late. Please check the delivery delay.', 'Resolved', 'Sam Lee'),

 ('demo:access:5845', 'Password reset · Customer #5845', 'I cannot access my account; the password reset email did not arrive.', 'Resolved', 'Sam Lee')

]

REFERENCES = tuple(row[0] for row in SCENARIOS)

def seed(session):

    for key, (title, content) in POLICIES.items():

        if not session.scalar(select(KnowledgeEntry).where(KnowledgeEntry.key == key)):

            session.add(KnowledgeEntry(key=key, title=title, content=content))

    session.flush()

    kb = tuple((k.key, k.content) for k in session.scalars(select(KnowledgeEntry).order_by(KnowledgeEntry.key)))

    from datetime import timedelta

    from .models import now

    anchor = now().replace(second=0, microsecond=0)
    ages = (30, 400, 180, 90, 3000, 1600)
    for index, (ref, title, text, status, assignee) in enumerate(SCENARIOS):

        if session.scalar(select(Conversation).where(Conversation.external_reference == ref)):

            continue

        created = anchor - timedelta(minutes=ages[index])

        data = AnalysisInput((('user', text),), kb)

        result = MockAIProvider().analyze(data)

        item = Conversation(title=title, external_reference=ref, status=status, priority=result['priority'], assignee=assignee, created_at=created, updated_at=created + timedelta(minutes=20), resolved_at=created + timedelta(hours=2) if status == 'Resolved' else None)

        session.add(item)

        session.flush()

        session.add(Message(conversation_id=item.id, role='user', content=text, created_at=created))

        if status == 'Resolved':
            result.update(reply_status='sent', reply_content='Synthetic operator update: reviewed the issue and confirmed the next step.')
        analysis = AIAnalysis(conversation_id=item.id, provider='mock', provider_version='3.0', input_digest=digest(data), result=result, created_at=created + timedelta(minutes=2))
        session.add(analysis)
        session.flush()

        session.add(AuditEvent(action='analysis.created', entity_id=analysis.id, details={'conversation_id': item.id, 'synthetic': True}, created_at=analysis.created_at))
        if assignee != 'Unassigned':
            session.add(AuditEvent(action='conversation.assignee.changed', entity_id=item.id, details={'conversation_id': item.id, 'before': 'Unassigned', 'after': assignee, 'synthetic': True}, created_at=created + timedelta(minutes=1)))
        session.add(AuditEvent(action='demo.created', entity_id=item.id, details={'conversation_id': item.id, 'synthetic': True}, created_at=created))
        if status != 'New':
            session.add(AuditEvent(action='conversation.status.changed', entity_id=item.id, details={'conversation_id': item.id, 'before': 'New', 'after': 'In review'}, created_at=created + timedelta(minutes=5)))
        if status == 'Resolved':
            session.add(Message(conversation_id=item.id, role='assistant', content='Synthetic operator update: reviewed the issue and confirmed the next step.', created_at=created + timedelta(minutes=15 + index * 5)))
            note = InternalNote(conversation_id=item.id, author=assignee, content='Synthetic resolution: policy reviewed and next steps confirmed.', created_at=created + timedelta(minutes=60))
            session.add(note)
            session.flush()
            session.add(AuditEvent(action='note.created', entity_id=note.id, details={'conversation_id': item.id, 'author': assignee, 'content': note.content, 'internal': True}, created_at=note.created_at))
            for action, minutes in (('approve', 10), ('mock-send', 15 + index * 5)):
                session.add(AuditEvent(action='reply.' + action, entity_id=analysis.id, details={'conversation_id': item.id, 'content': result['reply_content'], 'synthetic': True}, created_at=created + timedelta(minutes=minutes)))
            session.add(AuditEvent(action='conversation.status.changed', entity_id=item.id, details={'conversation_id': item.id, 'before': 'In review', 'after': 'Resolved'}, created_at=created + timedelta(hours=2)))
