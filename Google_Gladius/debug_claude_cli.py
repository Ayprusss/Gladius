#!/usr/bin/env python3
"""Debug script to test Claude CLI response parsing"""

import sys
from src.claude_client.cli_invoker import ClaudeClient
from src.schemas.planner_schema import PlannerOutput

def test_planner_invocation():
    """Test a simple planner invocation to debug response format"""

    print("=" * 80)
    print("DEBUGGING CLAUDE CLI RESPONSE PARSING")
    print("=" * 80)

    client = ClaudeClient()

    # Simple test prompt
    user_message = "Create a plan to add a hello world function to a Python file"
    system_prompt = "You are a software planning agent. Create a detailed implementation plan."

    # Get the schema
    json_schema = PlannerOutput.model_json_schema()

    print("\n[INFO] Testing Claude CLI invocation...")
    print(f"[INFO] Model: sonnet")
    print(f"[INFO] Schema fields required: {list(json_schema.get('required', []))}")
    print("\n" + "=" * 80)

    try:
        # Invoke Claude CLI
        result = client.invoke(
            user_message=user_message,
            system_prompt=system_prompt,
            json_schema=json_schema,
            model="sonnet"
        )

        print("\n" + "=" * 80)
        print("[SUCCESS] Claude CLI invocation successful!")
        print("=" * 80)
        print(f"\n[INFO] Result type: {type(result)}")
        print(f"[INFO] Result keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")

        # Try to validate with Pydantic
        print("\n[INFO] Attempting Pydantic validation...")
        validated = PlannerOutput.model_validate(result)

        print("[SUCCESS] Pydantic validation successful!")
        print(f"[INFO] Summary: {validated.summary[:100]}...")
        print(f"[INFO] Plan steps: {len(validated.plan)}")

        return True

    except Exception as e:
        print("\n" + "=" * 80)
        print("[ERROR] Exception occurred!")
        print("=" * 80)
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")

        import traceback
        print("\nFull traceback:")
        traceback.print_exc()

        return False

if __name__ == "__main__":
    success = test_planner_invocation()
    sys.exit(0 if success else 1)
