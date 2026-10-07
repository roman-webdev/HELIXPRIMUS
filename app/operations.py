"""Synchronous operational metrics. All timestamps are interpreted as UTC."""
from datetime import timedelta, timezone
from sqlalchemy import select
from .models import Conversation, Message, AIAnalysis, AuditEvent, now

SLA_MINUTES = {'High': 120, 'Medium': 480, 'Low': 1440}
OPERATORS = ('Unassigned', 'Alex Morgan', 'Sam Lee')
TRANSITIONS = {'New': ('In review',), 'In review': ('Resolved',), 'Resolved': ('In review',)}

def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)

def sla(item, at=None):
    target = SLA_MINUTES[item.priority]
    due = utc(item.created_at) + timedelta(minutes=target)
    elapsed = ((utc(item.resolved_at) if item.status == 'Resolved' and item.resolved_at else utc(at or now())) - utc(item.created_at)).total_seconds() / 60
    state = 'Overdue' if elapsed > target else 'At risk' if elapsed >= target * .8 and item.status != 'Resolved' else 'On track'
    return {'sla_target_minutes': target, 'sla_due_at': due, 'sla_state': state, 'sla_closed': item.status == 'Resolved'}

def distribution(items, field):
    result = {}
    for item in items:
        key = getattr(item, field)
        result[key] = result.get(key, 0) + 1
    return result

def mean(values):
    return round(sum(values) / len(values), 1) if values else None

def metrics(session):
    at = now()
    items = session.scalars(select(Conversation)).all()
    analyses = session.scalars(select(AIAnalysis).order_by(AIAnalysis.created_at, AIAnalysis.id)).all()
    latest = {a.conversation_id: a for a in analyses}
    events = session.scalars(select(AuditEvent)).all()
    messages = session.scalars(select(Message).where(Message.role == 'assistant').order_by(Message.created_at)).all()
    first = {}
    for message in messages:
        first.setdefault(message.conversation_id, utc(message.created_at))
    responses = [max(0, (first[c.id] - utc(c.created_at)).total_seconds() / 60) for c in items if c.id in first]
    resolutions = [(utc(c.resolved_at) - utc(c.created_at)).total_seconds() / 60 for c in items if c.resolved_at]
    approved = {e.entity_id for e in events if e.action == 'reply.approve'}
    sends = sum(e.action == 'reply.mock-send' for e in events)
    failures = sum(e.action == 'reply.mock-send.rejected' for e in events)
    intents = {}
    for c in items:
        intent = latest[c.id].result['intent'] if c.id in latest else 'Unanalyzed'
        intents[intent] = intents.get(intent, 0) + 1
    backlog = [c for c in items if c.status != 'Resolved']
    states = {key: sum(sla(c, at)['sla_state'] == key for c in backlog) for key in ('On track', 'At risk', 'Overdue')}
    trend = []
    for offset in range(6, -1, -1):
        day = (at - timedelta(days=offset)).date()
        trend.append({'date': day.isoformat(), 'created': sum(utc(c.created_at).date() == day for c in items), 'resolved': sum(bool(c.resolved_at) and utc(c.resolved_at).date() == day for c in items)})
    return {'total': len(items), 'open': len(backlog), 'resolved': len(items)-len(backlog), 'mock_sends': sends,
        'priority_distribution': distribution(items, 'priority'), 'status_distribution': distribution(items, 'status'),
        'assignee_distribution': distribution(items, 'assignee'), 'intent_distribution': intents,
        'backlog_by_priority': distribution(backlog, 'priority'), 'backlog_by_status': distribution(backlog, 'status'),
        'average_first_response_minutes': mean(responses), 'first_response_sample_size': len(responses),
        'average_resolution_minutes': mean(resolutions), 'resolution_sample_size': len(resolutions),
        'approval_rate': round(100 * len(approved & {a.id for a in analyses}) / len(analyses), 1) if analyses else None,
        'approval_denominator': len(analyses), 'mock_send_success_rate': round(100*sends/(sends+failures), 1) if sends+failures else None,
        'mock_send_attempts': sends+failures, 'sla_distribution': states, 'sla_at_risk': states['At risk'], 'sla_overdue': states['Overdue'], 'trend': trend, 'as_of': at}
