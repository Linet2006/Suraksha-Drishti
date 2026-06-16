import asyncio
from app.services.agents.trade_licence_agent.scraper import verify_trade_licence

async def main():
    payload = {"application_number": "BBMP/TL/001"}
    try:
        res = await verify_trade_licence(payload)
        print(res)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(main())
