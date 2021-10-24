import random
from rom.rom import snes_to_pc
from logic.helpers import Bosses
from logic.smbool import SMBool

class Synonyms(object):
    killSynonyms = [
        "massacre",
        "slaughter",
        "slay",
        "wipe out",
        "annihilate",
        "eradicate",
        "erase",
        "exterminate",
        "finish",
        "neutralize",
        "obliterate",
        "destroy",
        "wreck",
        "smash",
        "crush",
        "end",
        "eliminate",
        "terminate"
    ]
    alreadyUsed = []
    @staticmethod
    def getVerb(): 
        verb = random.choice(Synonyms.killSynonyms)
        while verb in Synonyms.alreadyUsed:
            verb = random.choice(Synonyms.killSynonyms)
        Synonyms.alreadyUsed.append(verb)
        return verb

class Goal(object):
    def __init__(self, name, clearFunc, checkAddr, exclusionList, text, useSynonym):
        self.name = name
        self.clearFunc = clearFunc
        # in bank $82, see objectives_pause.asm
        self.checkAddr = checkAddr
        self.rank = -1
        self.exclusionList = exclusionList
        self.cleared = False
        self.text = text
        self.useSynonym = useSynonym

    def setRank(self, rank):
        self.rank = rank

    def canClearGoal(self, smbm):
        return self.clearFunc(smbm)

    def setCleared(self, cleared):
        self.cleared = cleared

    def getText(self):
        out = "{}. ".format(self.rank)
        if self.useSynonym:
            out += self.text.format(Synonyms.getVerb())
        else:
            out += self.text
        assert len(out) < 28, "Goal text is too long: {}, max 28".format(len(out))
        return out

class Objectives(object):
    objectivesList = snes_to_pc(0x82f983)

    def __init__(self):
        self.goals = {
            "kill kraid": Goal("kill kraid", lambda sm: Bosses.bossDead(sm, 'Kraid'), 0xF98F,
                               ["kill G4"], "{} kraid", True),
            "kill phantoon": Goal("kill phantoon", lambda sm: Bosses.bossDead(sm, 'Phantoon'), 0xF997,
                                  ["kill G4"], "{} phantoon", True),
            "kill draygon": Goal("kill draygon", lambda sm: Bosses.bossDead(sm, 'Draygon'), 0xF99F,
                                 ["kill G4"], "{} draygon", True),
            "kill ridley": Goal("kill ridley", lambda sm: Bosses.bossDead(sm, 'Ridley'), 0xF9A7,
                                ["kill G4"], "{} ridley", True),
            "kill G4": Goal("kill G4", lambda sm: Bosses.allBossesDead(sm), 0xF9AF,
                            ["kill kraid", "kill phantoon", "kill draygon", "kill ridley"],
                            "{} golden four", True),
            "kill spore spawn": Goal("kill spore spawn", None, 0xF9C5,
                                     ["kill mini bosses"], "{} spore spawn", True),
            "kill botwoon": Goal("kill botwoon", None, 0xF9CD,
                                 ["kill mini bosses"], "{} botwoon", True),
            "kill crocomire": Goal("kill crocomire", None, 0xF9D5,
                                   ["kill mini bosses"], "{} crocomire", True),
            "kill bomb torizo": Goal("kill bomb torizo", None, 0xF9DD,
                                     ["kill mini bosses"], "{} bomb torizo", True),
            "kill golden torizo": Goal("kill golden torizo", None, 0xF9E5,
                                       ["kill mini bosses"], "{} golden torizo", True),
            "kill mini bosses": Goal("kill mini bosses", None, 0xF9ED,
                                     ["kill spore spawn", "kill botwoon", "kill crocomire", "kill bomb torizo", "kill golden torizo"],
                                     "{} mini bosses", True),
            "shaktool cleared path": Goal("shaktool cleared path", None, 0xFA08,
                                          [], "shaktool cleared its path", False),
            "finish scavenger hunt": Goal("finish scavenger hunt", None, 0xFA10,
                                          [], "finish scavenger hunt", False)
        }
        self.activeGoals = []
        self.nbActiveGoals = 0

    def addGoal(self, goalName):
        goal = self.goals[goalName]
        self.nbActiveGoals += 1
        goal.setRank(self.nbActiveGoals)
        self.activeGoals.append(goal)

    def setVanilla(self):
        self.addGoal("kill kraid")
        self.addGoal("kill phantoon")
        self.addGoal("kill draygon")
        self.addGoal("kill ridley")

    def setScavengerHunt(self, triggerEscape):
        if not triggerEscape:
            self.setVanilla()
        self.addGoal("finish scavenger hunt")

    def setRandom(self, nbGoals):
        pass

    def canClearGoals(self, smbm):
        result = SMBool(True)
        for goal in self.activeGoals:
            result = smbm.wand(result, goal.canClearGoal(smbm))
        return result

    def getGoalFromCheckFunction(self, checkFunction):
        for name, goal in self.goals.items():
            if goal.checkAddr == checkFunction:
                return goal
        assert True, "Goal with check function {} not found".format(hex(checkFunction))

    def readGoals(self, romFile):
        romFile.seek(Objectives.objectivesList)
        checkFunction = romFile.readWord()
        while checkFunction != 0x0000:
            goal = self.getGoalFromCheckFunction(checkFunction)
            self.activeGoals.append(goal)
            checkFunction = romFile.readWord()

    def writeGoals(self, romFile):
        # write check functions
        romFile.seek(Objectives.objectivesList)
        for goal in self.activeGoals:
            romFile.writeWord(goal.checkAddr)
        # list terminator
        romFile.writeWord(0x0000)

        # compute chars
        char2tile = {
            '.': 0x4A,
            '?': 0x4B,
            '!': 0x4C,
            ' ': 0x00,
            '%': 0x02,
            '*': 0x03,
            '0': 0x04,
            'a': 0x30,
        }
        for i in range(1, ord('z')-ord('a')+1):
            char2tile[chr(ord('a')+i)] = char2tile['a']+i
        for i in range(1, ord('9')-ord('0')+1):
            char2tile[chr(ord('0')+i)] = char2tile['0']+i

        # write text
        tileSize = 2
        lineLength = 32 * tileSize
        firstChar = 3 * tileSize
        # start at 8th line
        baseAddr = 0xB6F200 + lineLength * 8 + firstChar
        # space between two lines of text
        space = 3 if self.nbActiveGoals == 5 else 4
        for i, goal in enumerate(self.activeGoals):
            addr = baseAddr + i * lineLength * space
            text = goal.getText()
            romFile.seek(snes_to_pc(addr))
            for c in text:
                romFile.writeWord(0x3800 + char2tile[c])

        # write goal completed positions y in sprites OAM
        baseY = 0x40
        addr = snes_to_pc(0x82FD4D)
        spritemapSize = 5 + 2
        for i, goal in enumerate(self.activeGoals):
            y = baseY + i * space * 8
            # sprite center is at 128
            y = (y - 128) & 0xFF
            romFile.writeByte(y, addr+4 + i*spritemapSize)