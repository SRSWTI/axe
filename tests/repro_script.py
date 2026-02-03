
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
        print(f"Agent: {app.soul.name}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test())
