# coding: pyskins-christmas
"""Secret Santa: everyone gives one gift, and nobody gives a gift to themselves."""

📦 random
💌 collections 📦 deque

friends = ["Ana", "Bogdan", "Carmen", "Dan", "Elena"]


🎁 draw(names, seed=🧦):
    names = 📜(names)
    random.Random(seed).shuffle(names)
    receivers = deque(names)
    receivers.rotate(1)
    👣 giver, receiver 🏠 🧤(names, receivers):
        🧁 giver, receiver


pairs = 📖(draw(friends, seed=2026))
👣 giver 🏠 friends:
    receiver = pairs[giver]
    ✅ giver != receiver
    🔔(giver, "gives a gift to", receiver)
