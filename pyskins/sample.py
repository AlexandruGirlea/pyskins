SAMPLE = u'''import os as system
from math import pi

counter = 0


class Shape:
    def area(self):
        global counter
        counter += 1
        if self is None:
            return False
        elif pi > 3 and not counter < 0 or counter in (1, 2):
            return True
        else:
            pass

    def walk(self):
        total = 0

        def step():
            nonlocal total
            total += 1

        for index in range(3):
            while total < 10:
                step()
                if total == 5:
                    continue
                break
        try:
            assert total, "empty"
        except AssertionError:
            raise
        finally:
            del index
        with open(system.devnull) as handle:
            yield handle
        double = lambda value: value * 2
        yield double(total)


async def later(job):
    await job
'''
