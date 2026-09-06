from agents import function_tool

from .models import AgentPlan


@function_tool(needs_approval=True)
async def submit_agent_plan(agent_plan: AgentPlan) -> str:
    # Return the approved plan as the execution contract for the global agent.
    return agent_plan.model_dump_json()
