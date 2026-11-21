# coding: pyskins-christmas
"""Christmas countdown: how many sleeps until Christmas?"""

💌 datetime 📦 date


🎁 sleeps_until_christmas(today):
    christmas = date(today.year, 12, 25)
    🎅 today > christmas:
        christmas = date(today.year + 1, 12, 25)
    🛷 (christmas - today).days


🎁 message(sleeps):
    🎅 sleeps == 0:
        🛷 "It is Christmas! Ho ho ho!"
    🤶 sleeps == 1:
        🛷 "Only one more sleep. Hang up your stocking!"
    🤶 sleeps <= 24:
        🛷 🧵(sleeps) + " sleeps to go. Time to open the advent calendar."
    🦌:
        🛷 🧵(sleeps) + " sleeps to go. Santa is still making his list."


👣 day 🏠 (date(2026, 11, 21), date(2026, 12, 1), date(2026, 12, 24), date(2026, 12, 25)):
    🔔(day, "->", message(sleeps_until_christmas(day)))

🔔("Today:", message(sleeps_until_christmas(date.today())))
