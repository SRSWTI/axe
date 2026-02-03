import asyncio
from axe_cli.app import AxeCLI
from axe_cli.session import Session
from kaos.path import KaosPath

async def test():
    try:
        work_dir = KaosPath.cwd()
        session = await Session.create(work_dir)
        app = await AxeCLI.create(session)
        print(f"✅ App created successfully!")
        print(f"Model: {app.soul.model_name}")
        try:
           print(f"Agent: {app.soul.agent.name}")
        except:
           print(f"Agent name not accessible directly on soul")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
