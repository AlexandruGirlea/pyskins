# coding: pyskins-faces
"""Rocket launch: check the systems, count down, and lift off."""

🤩 time


🧐 Rocket:
    🤓 __init__(🙂, name, fuel):
        🙂.name = name
        🙂.fuel = fuel
        🙂.flying = 🙁

    🤓 check(🙂):
        🤔 🙂.fuel 😐 😑:
            😡 ValueError("nobody filled the tank")
        😌 🙂.fuel > 50 🤗 🙄 🙂.flying

    🤓 launch(🙂, wait=0.0):
        😬:
            ready = 🙂.check()
        😱 ValueError 🥸 problem:
            😛(🙂.name, "stays on the ground:", problem)
            😌 🙁
        😅:
            😛(🙂.name, "was checked")
        🤔 🙄 ready:
            😌 🙁
        🥱 second 😮 😁(3, 0, -1):
            😛(second)
            time.sleep(wait)
        🙂.flying = 😀
        😛(🙂.name, "has lifted off!")
        😌 😀


🥱 rocket 😮 (Rocket("Zorp One", 80), Rocket("Empty Can", 😑)):
    rocket.launch()
