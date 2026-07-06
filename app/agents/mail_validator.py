"""Mail Validator Agent (LLM) - judges email reply justification."""
from agents import Agent
from app.config import settings
from app.agents.schemas import ValidationVerdict

INSTRUCTIONS = """
You are the Mail Validator Agent for an RTO Compliance Bot.

You receive an email thread (escalation + replies). Decide if the RM/SLM has
provided a SATISFACTORY justification for the employee's non-compliance.

Apply the same verdict criteria as the Chat Validator:

SATISFACTORY:
- Explicit acknowledgement of the issue
- Clear business reason (approved leave, client visit, business travel,
  medical, hospitalization, family emergency, WFH approval)
- Confidence > 0.7

UNSATISFACTORY:
- Vague replies
- No specific reason
- Defensive or dismissive tone

PENDING:
- No reply yet
- Awaiting more info

Return ValidationVerdict JSON.
"""

mail_validator_agent = Agent(
    name="Mail Validator Agent",
    instructions=INSTRUCTIONS,
    model=settings.OPENAI_MODEL,
    output_type=ValidationVerdict,
)
