import asyncio

from kaos.path import KaosPath
from rich import print

from axe_cli.app import AxeCLI, enable_logging
from axe_cli.session import Session


async def main():
    enable_logging()
    session = await Session.create(KaosPath.cwd())
    instance = await AxeCLI.create(session)
    user_input = "Hello!"

    async for msg in instance.run(
        user_input=user_input,
        cancel_event=asyncio.Event(),
        merge_wire_messages=True,
    ):
        print(msg)

    # print the last assistant message
    print(instance.soul.context.history[-1])


if __name__ == "__main__":
    asyncio.run(main())
