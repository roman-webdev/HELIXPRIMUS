from typing import Protocol

from dataclasses import dataclass

import hashlib

import json

import re

@dataclass(frozen=True)

class AnalysisInput:

    messages: tuple[tuple[str, str], ...]

    knowledge: tuple[tuple[str, str], ...]

class AIProvider(Protocol):

    name: str

    version: str

    def analyze(self, data: AnalysisInput) -> dict: ...

def digest(data: AnalysisInput) -> str:

    raw = json.dumps({'messages': data.messages, 'knowledge': data.knowledge}, ensure_ascii=False, sort_keys=True)

    return hashlib.sha256(raw.encode()).hexdigest()

class MockAIProvider:

    name = 'mock'

    version = '3.0'

    def analyze(self, data: AnalysisInput) -> dict:
        result = self.classify(data)
        keywords = {'Billing issue': ('charged twice', 'duplicate payment'), 'account_access': ('login', 'access', 'password', 'locked'), 'cancellation_refund': ('cancel', 'refund', 'return'), 'order_delay': ('delay', 'late', 'задерж', 'опозд')}
        text = ' '.join(content for role, content in data.messages if role == 'user').casefold()
        evidence = [word for word in keywords.get(result['intent'], ()) if word in text]
        matched = bool(result['knowledge_citations'])
        result['confidence'] = {'intent': .96 if evidence else .55, 'priority': .90 if evidence else .60, 'sentiment': .78 if result['sentiment'] == 'Negative' else .65, 'kb_match': .95 if matched else 0.0}
        result['explanations'] = {
            'intent': 'Matched customer phrases: ' + ', '.join(evidence) + '. Ordered rules select this intent.' if evidence else 'No specific issue keywords matched; general inquiry fallback.',
            'priority': {'High': 'Payment duplication or account lockout needs prompt operator review.', 'Medium': 'Order or eligibility review follows the standard queue.', 'Low': 'General inquiry has no detected urgent issue.'}[result['priority']],
            'sentiment': 'Issue wording indicates friction; this is a rule estimate, not an emotion diagnosis.' if result['sentiment'] == 'Negative' else 'No explicit negative issue rule matched; neutral estimate.',
            'entities': 'Explicit customer references: ' + ', '.join(result['entities'].get('customer_numbers', [])) if result['intent'] == 'account_access' and result['entities'].get('customer_numbers') else ('Explicit order references: ' + ', '.join(result['order_numbers']) if result['order_numbers'] else 'No explicit #number reference found in customer text.'),
            'kb_match': 'Exact policy key for the selected intent: ' + ', '.join(result['knowledge_citations']) if matched else 'No corresponding policy exists in the knowledge library.'}
        result['evidence'] = evidence
        result['confidence_method'] = 'Fixed mock rule scores; not calibrated probabilities. Human review required.'
        return result

    def classify(self, data: AnalysisInput) -> dict:

        text = ' '.join(content for role, content in data.messages if role == 'user')

        orders = sorted(set(re.findall(r'#(\d+)', text)))

        billing = any(word in text.casefold() for word in ('charged twice', 'duplicate payment'))

        if billing:

            return {'intent': 'Billing issue', 'priority': 'High', 'sentiment': 'Negative', 'order_numbers': orders, 'issue': 'Duplicate payment', 'entities': {'order_numbers': orders}, 'knowledge_citations': [key for key, _ in data.knowledge if key == 'refund-policy-3.2'], 'summary': 'Customer reports a duplicate charge and requests a refund.', 'suggested_reply': f"Thank you for flagging this. I’m sorry about the duplicate charge for order #{orders[0] if orders else 'unknown'}. We’ll verify both transactions and, if a duplicate payment is confirmed, refund it to your original payment method under Refund Policy §3.2. We’ll share confirmation once the review is complete.", 'requires_human_review': True}

        folded = text.casefold()

        if any(word in folded for word in ('login', 'access', 'password', 'locked')):

            intent, priority, sentiment, key = 'account_access', 'High', 'Negative', 'account-access'

            summary = 'Customer cannot access their account.'

            reply = 'I’m sorry you cannot access your account. Please use the password reset link and check your inbox. If access remains blocked, we will escalate for identity verification. Never share your password or verification codes.'

        elif any(word in folded for word in ('cancel', 'refund', 'return')):

            intent, priority, sentiment, key = 'cancellation_refund', 'Medium', 'Neutral', 'cancellation-refund'

            summary = 'Customer requests cancellation or refund eligibility review.'

            reply = 'We will review the order status and cancellation eligibility. Unshipped orders may be cancelled; shipped orders require a return review. We will confirm eligibility before promising any refund.'

        elif any(word in folded for word in ('delay', 'late', 'задерж', 'опозд')):

            intent, priority, sentiment, key = 'order_delay', 'Medium', 'Negative', 'shipping-delay'

            summary = 'Customer reports a delivery delay.'

            reply = 'We will check the carrier status and share a confirmed update. We cannot promise a delivery date before verification.'

        else:

            intent, priority, sentiment, key = 'general_inquiry', 'Low', 'Neutral', None

            summary, reply = 'Customer inquiry requires review', 'Please share more details so we can assist.'

        return {'intent': intent, 'priority': priority, 'sentiment': sentiment, 'issue': summary, 'entities': {'customer_numbers' if intent == 'account_access' else 'order_numbers': orders}, 'order_numbers': [] if intent == 'account_access' else orders, 'summary': summary, 'suggested_reply': reply, 'knowledge_citations': [k for k, _ in data.knowledge if k == key], 'requires_human_review': True}



def get_provider(name: str) -> AIProvider:

    if name != 'mock':

        raise ValueError(f'Unsupported AI provider: {name}')

    return MockAIProvider()
