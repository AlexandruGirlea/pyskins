# coding: pyskins-faces
"""Guess the number: one robot picks a number, and another robot finds it."""

🤩 random


🤓 play(secret, low=1, high=100):
    tries = 0
    😵 😀:
        tries += 1
        guess = (low + high) // 2
        🤔 guess == secret:
            😌 tries
        🤨 guess < secret:
            😛(guess, "is too low")
            low = guess + 1
        🙃:
            😛(guess, "is too high")
            high = guess - 1


random.seed(7)
secret = random.randint(1, 100)
tries = play(secret)
😛("Found", secret, "in", tries, "tries")
😤 tries <= 7, "halving the range never needs more than 7 tries"
