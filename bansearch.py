# Licensed under the MIT license, see https://github.com/Fuchs/zncscripts/blob/master/LICENSE
# Based on the work of and cooperation with MuffinMedic, https://github.com/MuffinMedic

import znc
import fnmatch
import re
import time

class bansearch(znc.Module):

    module_types = [znc.CModInfo.NetworkModule]

    def OnLoad(self, args, message):
        self.chanstocheck = {}
        self.channelschecked = []
        self.whos = {}
        self.modes = "bq"
        self.quietsDone = {}; self.bansDone = {}; self.exceptsDone = {}
        self.globpattern = re.compile("([\[\]])")
        return True

    def OnRaw(self, message):
        message = (message.s).lower().split()
        if message[1] == '354':
            self.setuserinfo(message)
        try:
            if self.chanstocheck[message[3]]:
                if message[1] == '348':
                    self.getbans(False, message, "e")
                    return znc.HALTCORE
                elif message[1] == '349':
                    self.getbans(True, message, "e")
                elif message[1] == '367':
                    self.getbans(False, message, "b")
                    return znc.HALTCORE
                elif message[1] == '368':
                    self.getbans(True, message, "b")
                    return znc.HALTCORE
                elif message[1] == '728':
                    self.getbans(False, message, "q")
                    return znc.HALTCORE
                elif message[1] == '729':
                    self.getbans(True, message, "q")
                    return znc.HALTCORE
                elif message[1] == '324':
                    mchan = message[3]
                    cmodes = message[4]
                    nick = self.chanstocheck[mchan]
                    user = self.whos[nick]
                    if user[4] == "0":
                        match = re.search("\+[^-]*r", cmodes)
                        if match:
                            self.PutModule("\x02{}\x02 can not join \x02{}\x02 due to \x02registered only (+r) mode\x02 in place.".format(nick, mchan))
                    match = re.search("\+[^-]*i", cmodes)
                    if match:
                        self.PutModule("Channel \x02{}\x02 is \x02invite only (+i)\x02, check invexes (/mode {} +I).".format(mchan, mchan))
        except:
            pass

    def setuserinfo(self, message):
        if message[5] in self.chanstocheck.values():
            nick = message[5]
            ident = message[3]
            host = message[4]
            gecos = ' '.join(message[7:])[1:]
            account = message[6]
            self.whos[nick] = (nick, ident, host, gecos, account)

    def getbans(self, IsEnd, message, type):
        channel = message[3]

        if type == "b" or type == "e":
            ban = message[4]
            stamp = message[6]
        elif type == "q":
            ban = message[5]
            stamp = message[7]

        if IsEnd:
            self.check(IsEnd, channel, None, type, None)
        elif not ban.startswith('$'):
            nuh = self.splitircban(ban)
            self.check(IsEnd, channel, nuh, type, stamp)
        elif "$" in ban:
            self.check(IsEnd, channel, ban, type, stamp)

    def check(self, IsEnd, chan, ban, type, stamp):
        if IsEnd:
            if type == "b":
                self.bansDone[chan] = True
            elif type == "q":
                self.quietsDone[chan] = True
            elif type == "e":
                self.exceptsDone[chan] = True
            if self.quietsDone[chan] and self.bansDone[chan] and self.exceptsDone[chan]:
                self.chanstocheck.pop(chan, None)
                self.PutModule("Check in {} complete.".format(chan))
        for channel, nick in self.chanstocheck.items():
            if chan == channel:
                user = self.whos[nick]
                if '$' not in ban:
                    if self.globmatch(user[0], ban[0]) and self.globmatch(user[1], ban[1]) and self.globmatch(user[2], ban[2]):
                        self.printban(user, chan, ban, False, type, stamp)
                else:
                    if "$x" in ban:
                        borig = ban
                        ban = self.splitircuser(ban)
                        if self.globmatch(user[0], ban[0]) and self.globmatch(user[1], ban[1]) and self.globmatch(user[2], ban[2]) and self.globmatch(user[3], ban[3]):
                            self.printban(user, chan, borig, True, type, stamp)
                    elif "$j" in ban:
                        jchan = ban.split(':')[1]
                        if "$" in jchan: 
                            jchan = jchan.split('$')[0]
                        if not jchan in self.channelschecked:
                            self.PutModule("Checking for bans on {} in {} as well due to $j".format(nick, jchan))
                            self.channelschecked.append(jchan)
                            self.chanstocheck[jchan] = nick
                            if "q" not in self.modes:
                                self.quietsDone[jchan] = True
                            if "b" not in self.modes:
                                self.bansDone[jchan] = True
                            if "e" not in self.modes:
                                self.exceptsDone[jchan] = True
                            self.PutIRC("MODE {} {}".format(jchan, self.modes))
                        else:
                            self.PutModule("Not checking {} again as it was already checked".format(jchan))
                    elif "$~a" in ban:
                        if user[4] == "0":
                            self.printban(user, chan, ban, True, type, stamp)
                    elif "$a" in ban:
                        extban = ban.split(':')[1]
                        if self.globmatch(user[4], extban):
                            self.printban(user, chan, ban, True, type, stamp)

    def formatAge(self, when):
        now = time.time()
        elapsed = int(now) - int(when)

        # minutes
        elapsed = elapsed // 60

        if elapsed < 1:
            return "seconds"
        if elapsed == 1:
            return "1 minute"
        if elapsed < 60:
            return str(elapsed) + " minutes"

        # hours
        elapsed = elapsed // 60
        if elapsed == 1:
            return "1 hour"
        if elapsed < 24:
            return str(elapsed) + " hours"

        #days
        elapsed = elapsed // 24
        if elapsed == 1:
            return "1 day"
        return str(elapsed) + " days"

    def printban(self, user, chan, ban, ext, type, stamp):
        userban = "{}!{}@{}".format(user[0], user[1], user[2])
        if user[4] == "0":
            account = "not identified"
        else:
            account = user[4]
        if not ext:
            if ban[3]:
                ban = "{}!{}@{}${}".format(ban[0], ban[1], ban[2], ban[3])
            else:
                ban = "{}!{}@{}".format(ban[0], ban[1], ban[2])

        stamp = self.formatAge(stamp)

        if type == "b":
            self.PutModule("\x02{}\x02 (account: {}, GECOS: {}) \x02banned\x02 in \x02{}\x02 with ban \x02{}\x02 (\x02{}\x02 ago).".format(userban, account, user[3], chan, ban, stamp))
        elif type == "q":
            self.PutModule("\x02{}\x02 (account: {}, GECOS: {}) \x02quieted\x02 in \x02{}\x02 with quiet \x02{}\x02 (\x02{}\x02 ago).".format(userban, account, user[3], chan, ban, stamp))
        elif type == "e":
            self.PutModule("\x02{}\x02 (account: {}, GECOS: {}) \x02excepted\x02 in \x02{}\x02 with exception \x02{}\x02 (\x02{}\x02 ago).".format(userban, account, user[3], chan, ban, stamp))

    def splitircuser(self, user):
        if "$x" in user:
            user = user.split(':')[1]
            gecos = user.split('#')[1]
        else:
            gecos = None
        nick = user.split('!')[0]
        ident = user.split('!')[1].split('@')[0]
        host = user.split('@')[1].split('#')[0]
        return (nick, ident, host, gecos)

    def splitircban(self, ban):
        if "$" in ban:
            user = ban.split('$')[0]
            forward = ban.split('$')[1]
        else:
            forward = None
        nick = ban.split('!')[0]
        ident = ban.split('!')[1].split('@')[0]
        host = ban.split('@')[1].split('$')[0]
        return (nick, ident, host, forward)


    def getbaninfo(self, nick, chan):
        self.chanstocheck[chan] = nick
        self.channelschecked.append(chan)
        self.PutIRC("WHO {} %nuhar".format(nick))
        self.PutIRC("MODE {}".format(chan))
        self.PutIRC("MODE {} {}".format(chan, self.modes))

    def OnModCommand(self, command):
        self.channelschecked = []
        self.chanstocheck = {}
        self.whos.clear()
        commands = command.lower().split()
        if len(commands) > 3:
            self.modes = commands[3]

        if commands[0] == "check":
            try:
                if "#" in commands[1]:
                    chan = commands[1]
                    nick = commands[2]
                elif "#" in commands[2]:
                    chan = commands[2]
                    nick = commands[1]
                else:
                    self.PutModule("Syntax: check <user> <#channel> [modes]")
                if "q" not in self.modes:
                    self.quietsDone[chan] = True
                if "b" not in self.modes:
                    self.bansDone[chan] = True
                if "e" not in self.modes:
                    self.exceptsDone[chan] = True
                self.getbaninfo(nick, chan)
            except:
                self.PutModule("Syntax: check <user> <#channel> [modes]")
        else:
            self.help()

    def help(self):
        # For pre 1.7.* znc use the below line for prettier output
        # help = znc.CTable(250)
        help = znc.CTable()
        help.AddColumn("Command")
        help.AddColumn("Arguments")
        help.AddColumn("Description")
        help.AddRow()
        help.SetCell("Command", "check")
        help.SetCell("Arguments", "<user> <#channel> [modes]")
        help.SetCell("Description", "Checks to see if an online user is banned in a channel, optionally set modes (default: bq)")
        help.AddRow()
        help.SetCell("Command", "help")
        help.SetCell("Arguments", "")
        help.SetCell("Description", "Display this output")

        self.PutModule(help)

    def globmatch(self, string, compare):
        escaped = self.globpattern.sub("[\g<1>]", compare)
        return fnmatch.fnmatch(string, escaped)
