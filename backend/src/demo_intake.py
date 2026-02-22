#!/usr/bin/env python3
"""
Demo script for HomeDesigner voice intake system.
Tests the full flow: create session → intake turns → finalize → generate Miro board.

Usage:
    python backend/src/demo_intake.py

This simulates a user conversation, collects preferences into a design brief,
and generates a Miro board at the end.
"""

import asyncio
import httpx
import json
import sys
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8100"
DEMO_TURNS = [
    "I want to design my living room and home office",
    "Modern and minimalist style",
    "My budget is 8000 euros",
    "I need a large sofa and a standing desk",
    "I don't like dark colors or leather furniture",
    "Perfect, let's go ahead!",
]


async def demo_flow():
    """Run the demo intake flow."""
    async with httpx.AsyncClient(timeout=30) as client:
        print("=" * 60)
        print("HomeDesigner Voice Intake Demo")
        print("=" * 60)

        # 1. Create session
        print("\n[1] Creating new session...")
        try:
            res = await client.post(f"{BASE_URL}/session/new")
            res.raise_for_status()
            session_id = res.json()["session_id"]
            print(f"✓ Session created: {session_id}")
        except Exception as e:
            print(f"✗ Failed to create session: {e}")
            return

        # 2. Get initial session state
        print("\n[2] Getting session status...")
        try:
            res = await client.post(
                f"{BASE_URL}/tool/kb_get",
                json={"session_id": session_id},
            )
            res.raise_for_status()
            session_state = res.json()
            print(f"✓ Initial status: {session_state['status']}")
            print(f"✓ Missing fields: {session_state['missing_fields']}")
        except Exception as e:
            print(f"✗ Failed to get status: {e}")
            return

        # 3. Run intake turns
        print("\n[3] Running intake conversation...")
        done = False
        for i, user_text in enumerate(DEMO_TURNS, 1):
            print(f"\n  Turn {i}:")
            print(f"  User: {user_text}")

            try:
                res = await client.post(
                    f"{BASE_URL}/voice_intake/turn",
                    json={
                        "session_id": session_id,
                        "user_text": user_text,
                    },
                )
                res.raise_for_status()
                result = res.json()

                assistant_text = result.get("assistant_text", "")
                missing_fields = result.get("missing_fields", [])
                done = result.get("done", False)

                print(f"  Agent: {assistant_text}")
                print(f"  Missing: {missing_fields if missing_fields else 'None'}")
                print(f"  Done: {done}")

            except Exception as e:
                print(f"  ✗ Error: {e}")
                return

            if done:
                print(f"\n✓ Conversation complete at turn {i}")
                break

        if not done:
            print("\n⚠ Conversation did not complete, but continuing to finalize...")

        # 4. Finalize and generate Miro board
        print("\n[4] Finalizing and generating Miro board...")
        try:
            res = await client.post(
                f"{BASE_URL}/voice_intake/finalize",
                json={"session_id": session_id},
            )
            res.raise_for_status()
            finalize_result = res.json()
            miro_url = finalize_result.get("miro_board_url", "")
            print(f"✓ Miro board URL: {miro_url}")
        except Exception as e:
            print(f"✗ Failed to finalize: {e}")
            return

        # 5. Get final session state
        print("\n[5] Getting final session state...")
        try:
            res = await client.get(f"{BASE_URL}/session/{session_id}")
            res.raise_for_status()
            final_session = res.json()
            print(f"✓ Final status: {final_session['status']}")
            print(f"✓ Brief collected:\n{json.dumps(final_session['brief'], indent=2)}")
        except Exception as e:
            print(f"✗ Failed to get final state: {e}")
            return

        print("\n" + "=" * 60)
        print("✓ Demo completed successfully!")
        print("=" * 60)
        print(f"\nSession ID: {session_id}")
        print(f"Miro Board: {miro_url}")


if __name__ == "__main__":
    print("Starting demo... (make sure backend is running on http://localhost:8100)")
    try:
        asyncio.run(demo_flow())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        sys.exit(1)
