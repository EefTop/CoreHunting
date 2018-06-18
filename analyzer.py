import re
import time

from functools import cmp_to_key
from pprint import pprint


def parse_line(line):
    line = line.lower()
    line = re.sub("(?<=[a-z])(?=\\d)|(?<=\\d)(?=[a-z])|\\.", " ", line)
    line = line.replace("w", "").replace(",", " ").replace("/", " ").replace(" and ", "").strip()
    line = line.replace("  ", " ")
    line = re.sub("(dead|gone|d)", "0", line)
    return line


def get_worlds():
    return [1, 2, 4, 5, 6, 9, 10, 12, 14, 15, 16, 18, 21, 22, 23, 24, 25, 26, 27, 28, 30, 31, 32, 35, 36, 37, 39
        , 40, 42, 44, 45, 46, 48, 49, 50, 51, 52, 53, 54, 56, 58, 59, 60, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72
        , 73, 74, 76, 77, 78, 79, 82, 83, 84, 85, 86, 87, 88, 89, 91, 92, 96, 98, 99, 100, 103, 104, 105, 114
        , 115, 116, 117, 119, 123, 124, 134, 137, 138, 139, 140]


def get_core_name(argument):
    switcher = {
        'c': "Cres",
        'cres': "Cres",
        'sword': "Sword",
        'edicts': "Sword",
        'sw': "Sword",
        'juna': "Juna",
        'j': "Juna",
        'seren': "Seren",
        'se': "Seren",
        'aagi': "Aagi",
        'a': "Aagi",
    }
    return switcher.get(argument, "nothing")


MAPPING = {'Cres': 0,
           'Sword': 1,
           'Juna': 2,
           'Seren': 3,
           'Aagi': 4}


def compare(tup1, tup2):
    a, (b, c) = tup1
    x, (y, z) = tup2
    if isinstance(b, int) and isinstance(y, int):
        return 1
    if isinstance(b, str) and isinstance(y, int):
        return -1
    elif isinstance(b, int) and isinstance(y, str):
        return 1
    elif isinstance(b, str) and isinstance(y, str):
        return -1 if MAPPING[b] < MAPPING[y] else 1
    return -1 if b < y else 1


class Analyzer:

    def __init__(self):
        self.worlds = {}
        for w in get_worlds():
            self.worlds[w] = [0, 0]

    def analyze_call(self, message):
        parsed = parse_line(message)
        split = parsed.split()
        if len(split) != 2:
            return
        world = split[0]
        call = split[1]

        if not world.isdigit():
            return

        world = int(world)
        if world not in get_worlds():
            return "{} is not a p2p english world".format(world)

        if call.isdigit():
            flints_filled = int(call)
            if 0 <= flints_filled <= 5:
                self.worlds[world] = [flints_filled, time.time()]
        else:
            if str(call) in ['reset', 'r']:
                return
            elif str(call) in ['cres', 'c', 'sword', 'edicts', 'sw', 'juna', 'j', 'seren', 'se', 'aagi', 'a']:
                core = str(call)
                core = get_core_name(core.lower())
                self.worlds[world] = [core, time.time()]
        # else. check for cres/sword/juna/seren/aagi/reset etc
        return self.get_order()

    def get_order(self):
        my_list = self.worlds.items()
        s = sorted(my_list, key=cmp_to_key(compare))
        pprint(s)
        res = []
        for key, value in s:
            if value[0] == 0:
                break
            if isinstance(value[0], str):
                res.append("w{}({})".format(key, value[0]))
            elif isinstance(value[0], int):
                res.append("w{}({}/6)".format(key, value[0]))
        return " -> ".join(res)
