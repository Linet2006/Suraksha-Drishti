import asyncio
import os
import sys

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
sys.path.append(root_dir)

from app.services.agents.udyam_agent.scraper import verify_udyam_number

async def main():
    try:
        res = await verify_udyam_number("UDYAM-MH-01-0000021")
        print("Success:", res)
    except Exception as e:
        print("Error:", repr(e))

if __name__ == "__main__":
    asyncio.run(main())
