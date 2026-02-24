# Escalation Rules — Customer Success FTE

## Hard Escalation Triggers (NEVER attempt to resolve — escalate immediately)

### 1. Pricing Inquiry
**Trigger phrases**: "how much", "pricing", "cost", "price", "quote", "discount",
"upgrade plan", "downgrade", "cancel subscription", "refund", "billing inquiry"
**Reason code**: `pricing_inquiry`
**Action**: "Our pricing specialist will be in touch. I've flagged your inquiry."

### 2. Refund Request
**Trigger phrases**: "refund", "money back", "charge back", "dispute charge",
"cancel and refund", "overcharged"
**Reason code**: `refund_request`
**Action**: Forward to billing@cloudsyncpro.com

### 3. Legal Language
**Trigger phrases**: "lawyer", "attorney", "sue", "lawsuit", "legal action",
"court", "GDPR complaint", "data breach", "regulatory"
**Reason code**: `legal_language`
**Action**: Do NOT respond to the substance — escalate immediately to legal team

### 4. Negative Sentiment
**Trigger**: Sentiment score < 0.3 (detected anger, frustration, threats)
**Trigger phrases**: "this is ridiculous", "worst product", "I hate", "useless",
"terrible", "scam", "fraud", "you suck", profanity
**Reason code**: `negative_sentiment`
**Action**: Acknowledge empathetically first, then escalate if unresolved

### 5. Explicit Human Request
**Trigger phrases (any channel)**: "talk to a human", "speak to someone",
"real person", "human agent", "customer service rep"
**WhatsApp shortcuts**: "human", "agent", "representative", "person"
**Reason code**: `explicit_human_request`
**Action**: "I'm connecting you with a team member right away."

### 6. Repeated Search Failure
**Trigger**: Agent cannot find relevant knowledge base entry after 2 search attempts
**Reason code**: `knowledge_not_found`
**Action**: "I don't have enough information to help with this. A specialist will follow up."

## Soft Escalation (attempt once, then escalate if customer unsatisfied)

- Complex multi-part technical issues (>3 unresolved steps)
- Data loss reports (escalate after initial acknowledgement)
- Account access issues after 2 failed resolution attempts

## Escalation Message Templates

### Email
> "Thank you for reaching out to CloudSync Pro. I've escalated your case to
> our specialist team who will follow up within 4 business hours. Your reference
> number is [TICKET_ID]. We apologise for any inconvenience."

### WhatsApp
> "I've connected you with our team 🤝 Someone will follow up within 4 hours.
> Ref: [TICKET_ID]"

### Web Form
> "Your case has been escalated to our specialist team. You'll receive an email
> update within 4 business hours. Reference: [TICKET_ID]"
