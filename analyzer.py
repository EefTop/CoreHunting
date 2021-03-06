import math
import os
import re
import time
import random
import json


def parse_line(line):
    line = line.lower()
    line = re.sub("(?<=[a-z])(?=\\d)|(?<=\\d)(?=[a-z])|\\.", " ", line)
    line = re.sub("^(world|w)", "", line)
    line = line.replace("  ", " ")
    line = re.sub("( dead| gone| d)", " 0", line)
    return line


_save_file = "saved_worlds.json"
_save_stats= "saved_stats.json"
_all_worlds = {1, 2, 4, 5, 6, 9, 10, 12, 14, 15, 16, 18, 21, 22, 23, 24, 25, 26, 27, 28, 30, 31, 32, 35, 36, 37, 39, 40,
               42, 44, 45, 46, 48, 49, 50, 51, 52, 53, 54, 56, 58, 59, 60, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72,
               73, 74, 76, 77, 78, 79, 82, 83, 84, 85, 86, 87, 88, 89, 91, 92, 96, 98, 99, 100, 103, 104, 105, 114, 115,
               116, 117, 119, 123, 124, 134, 137, 138, 139, 140}


def _special_worlds():
    aus = "Australia/NZ world, bad servers"
    legacy = "Legacy only world, try to avoid"
    t1500 = "1500 total world"
    return {12: aus, 15: aus, 49: aus, 50: aus, 18: legacy, 115: legacy, 137: legacy, 52: "VIP world", 66: "EOC world",
            96: "Quick chat world, avoid", 48: "2600 total world", 30: "2000 total world", 86: t1500, 114: t1500}


_special_worlds = _special_worlds()


def get_core_name(argument):
    switcher = {
        'c': "Cres",
        'cres': "Cres",
        'sword': "Sword",
        'edicts': "Sword",
        'sw': "Sword",
        'e': "Sword",
        'juna': "Juna",
        'j': "Juna",
        'seren': "Seren",
        'se': "Seren",
        'aagi': "Aagi",
        'a': "Aagi",
    }
    return switcher.get(argument, "0")


MAPPING = {'Cres': 0,
           'Sword': 1,
           'Juna': 2,
           'Seren': 3,
           'Aagi': 4,
           6: 6}


def _json_keys_to_str(x):
    if isinstance(x, dict):
        return {int(k): v for k, v in x.items()}
    return x


class Analyzer:

    def __init__(self, client):
        self.worlds = {}
        self.load()
        self.client = client
        self.table_messages = {}  # dict of tables with messages of the table
        self.scouts = {} # current scouts with their assigned worlds

    async def analyze_call(self, message):
        parsed = parse_line(message.content)
        split = parsed.split()
        if len(split) != 2:
            return
        world = split[0]
        call = split[1]

        if not world.isdigit():
            return

        world = int(world)
        if world in _special_worlds:
            if str(message.channel.type) != "private":
                await self.client.send_message(message.channel, "NOTE, w{} is a {}.".format(world, _special_worlds[world]))

        if world not in self.worlds:
            await self.client.send_message(message.channel, "{} is not a p2p english world".format(world))
            return

        #clear worlds from scouts
        for id in self.scouts:
            for to_be_scouted in self.scouts[id]["worlds"]:
                if to_be_scouted == world:
                    self.scouts[id]["worlds"].remove(world)
        
        if call.isdigit():
            flints_filled = int(call)
            if 0 <= flints_filled <= 6:
                # rescout worlds with more cores faster to stay on top of what is next
                # extra time till rescout is 26 mins -4 min for each plinth
                # for now this also includes 5/6 (this has 6 mins) if this gives a problem ill change it.
                extra_time = (26 - flints_filled * 4) * 60 
                self.worlds[world] = (flints_filled, time.time(), time.time() + extra_time)
                id = message.author.id
                self.check_make_scout(id, message.author.name)
                self.scouts[id]["stats"][str(flints_filled) + "/6 calls"] += 1
                self.scouts[id]["stats"]["calls"] += 1
        else:
            if str(call) in ['reset', 'r']:
                return
            elif str(call) in ['cres', 'c', 'sword', 'edicts', 'sw', 'juna', 'j', 'seren', 'se', 'aagi', 'a']:
                core = str(call)
                core = get_core_name(core.lower())
                extra_time = 26 * 60 # default time till rescout on a 0/6 world
                self.worlds[world] = (core, time.time(), time.time() + extra_time)
                id = message.author.id
                self.check_make_scout(id, message.author.name)
                self.scouts[id]["stats"]["core calls"] += 1
                self.scouts[id]["stats"]["calls"] += 1
                
        # else. check for cres/sword/juna/seren/aagi/reset etc
        await self.relay(message.channel)

    async def relay(self, channel):
        relay_message = self.get_table()
        for ch, msg in self.table_messages.items():
            if ch == channel:
                await self.client.delete_message(self.table_messages[channel])
            else:
                await self.client.edit_message(msg, relay_message)
        
        if str(channel.type) != "private":
            self.table_messages[channel] = await self.client.send_message(channel, relay_message)

    def get_table(self):
        active_list = [(k, v) for k, v in self.worlds.items() if (isinstance(v[0], str) or v[0] == 6) and time.time() - v[1] < 150]
        next_list = [(k, v) for k, v in self.worlds.items() if isinstance(v[0], int) and 6 > v[0] > 0 and time.time() - v[1] < 60*60]
        next_list_s = sorted(next_list, key=lambda v: (-v[1][0], v[1][1]))
        active_list_s = sorted(active_list, key=lambda v: (MAPPING[v[1][0]], -v[1][1]))

        n = max(len(next_list_s), len(active_list_s), 1)
        table = "|   Active   |      Next      |\n"
        table += "-" * (3 + 12 + 16) + "\n"
        for i in range(n):
            if i < len(active_list_s):
                (world, value) = active_list_s[i]
                s = "w" + str(world) + "(" + str(value[0]) + ")"
                l = len(s)
                s = " " * int(math.ceil(6 - l / 2)) + s + " " * int(math.floor(6 - l / 2))
                table += "|" + s + "|"
            else:
                table += "|" + " " * 12 + "|"
            if i < len(next_list_s):
                (world, value) = next_list_s[i]
                age = str(math.floor((time.time() - value[1]) / 60))
                s = "w" + str(world) + "(" + str(value[0]) + "/6) " + age + "m"
                l = len(s)
                s = " " * int(math.ceil(8 - l / 2)) + s + " " * int(math.floor(8 - l / 2))
                table += s + "|\n"
            elif i - 2 < len(next_list_s):
                table += " Nil, scout pls" + " " + "|\n"
            else:
                table += "" + " " * 16 + "|\n"

        return "```" + table + "```"

    async def stats(self, channel, *id):
        if len(id) >= 1 and len(id[0]) >= 1:
            if len(id[0][0]) > 3:
                if id[0][0][2] == "!":
                    id = id[0][0][3:-1]
                else:
                    id = id[0][0][2:-1]
        if id in self.scouts:
            response = "these are all the stats of " + self.scouts[id]["name"] + ": \n"
            for stat in self.scouts[id]["stats"]:
                response += stat + ": " + str(self.scouts[id]["stats"][stat]) + " "
        else:
            response = "these are all the stats of all the scouts:"
            for id in self.scouts:
                response += "\n" + self.scouts[id]["name"]
                for stat in self.scouts[id]["stats"]:
                    response += " " + stat + ": " + str(self.scouts[id]["stats"][stat])
        await self.client.send_message(channel, response) 

    # make stats for scout mainly
    # checks all field that a scout can use and makes them if not existent
    # add new stats on this list
    def check_make_scout(self, scout, name):
        if scout not in self.scouts:
            self.scouts[str(scout)] = {}
        if "name" not in self.scouts[scout]:
            self.scouts[scout]["name"] = name
        if "time" not in self.scouts[scout]:
            self.scouts[scout]["time"] = 0
        if "stats" not in self.scouts[scout]:
            self.scouts[scout]["stats"] = {}
        if "scouts" not in self.scouts[scout]["stats"]:
            self.scouts[scout]["stats"]["scouts"] = 0
        if "calls" not in self.scouts[scout]["stats"]:
            self.scouts[scout]["stats"]["calls"] = 0
        if "0/6 calls" not in self.scouts[scout]["stats"]:
            self.scouts[scout]["stats"]["0/6 calls"] = 0
        if "1/6 calls" not in self.scouts[scout]["stats"]:
            self.scouts[scout]["stats"]["1/6 calls"] = 0
        if "2/6 calls" not in self.scouts[scout]["stats"]:
            self.scouts[scout]["stats"]["2/6 calls"] = 0
        if "3/6 calls" not in self.scouts[scout]["stats"]:
            self.scouts[scout]["stats"]["3/6 calls"] = 0
        if "4/6 calls" not in self.scouts[scout]["stats"]:
            self.scouts[scout]["stats"]["4/6 calls"] = 0
        if "5/6 calls" not in self.scouts[scout]["stats"]:
            self.scouts[scout]["stats"]["5/6 calls"] = 0
        if "core calls" not in self.scouts[scout]["stats"]:
            self.scouts[scout]["stats"]["core calls"] = 0
        if "worlds" not in self.scouts[scout]:
            self.scouts[scout]["worlds"] = []
            

    # command = ?scout *amount
    # optional parameter amount can range from 1 to 10
    # tell s the user to scout a list of worlds
    async def get_scout_info(self, channel, username, scout, args):
        id = scout.id
        if id in self.scouts and len(self.scouts[id]["worlds"]) > 0 and self.scouts[id]["time"] > time.time():
            await self.client.send_message(scout, "you still need to scout {}".format(self.scouts[id]["worlds"]))
            return   
        else:
            self.check_make_scout(id, username)
            extra_time = 15 * 60
            self.scouts[id]["time"] = time.time() + extra_time
            self.scouts[id]["stats"]["scouts"] += 1
        
        amount = 10
        if len(args) >= 1:
            if args[0].isdigit():
                amount = max(1, min(10, int(args[0])))
        all_worlds = [k for k, v in self.worlds.items() if time.time() - v[2] > 0]
        if len(all_worlds) > 1:
            if amount > len(all_worlds):
                amount = len(all_worlds)
                i = 0
            else:
                i = random.randint(0, len(all_worlds)-amount)
            result = all_worlds[i:i+amount]
            worlds = all_worlds[i:i+amount]
            for j in range(i, i + amount):
                world = self.worlds[all_worlds[j]]
                extra_time = 15 * 60
                self.worlds[all_worlds[j]] = [world[0], world[1], time.time() + extra_time]
                
            response = "error getting worlds"
            if len(result) == 1:
                response = "{}, please scout world {}".format(username, result[0])
            elif len(result) >= 2:
                response = "{}, please scout the following worlds {}".format(username, result)
            self.scouts[id]["worlds"] = worlds
            await self.client.send_message(scout, response)
            await self.client.send_message(channel, response)
        
    def reset(self):
        self.worlds = {w: (0, 0, 0) for w in _all_worlds}

    def save(self):
        with open(_save_file, 'w') as f:
            json.dump(self.worlds, f, indent=2)

    def load(self):
        if os.path.isfile(_save_file):
            with open(_save_file, 'r') as f:
                self.worlds = json.load(f, object_hook=_json_keys_to_str)
        else:
            self.reset()
