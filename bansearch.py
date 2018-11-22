# Licensed under the MIT license, see https://github.com/Fuchs/zncscripts/blob/master/LICENSE
# Based on the work of and cooperation with MuffinMedic, https://github.com/MuffinMedic

import znc
import fnmatch
import re

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
        if type == "b" or type == "e":
            ban = message[4]
        elif type == "q":
            ban = message[5]
        if IsEnd:
            self.check(IsEnd, message[3], None, type)
        elif not ban.startswith('$'):
            nuh = self.splitircban(ban)
            self.check(IsEnd, message[3], nuh, type)
        elif "$" in ban:
            self.check(IsEnd, message[3], ban, type)

    def check(self, IsEnd, chan, ban, type):
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
                        self.printban(user, chan, ban, False, type)
                else:
                    if "$x" in ban:
                        borig = ban
                        ban = self.splitircuser(ban)
                        if self.globmatch(user[0], ban[0]) and self.globmatch(user[1], ban[1]) and self.globmatch(user[2], ban[2]) and self.globmatch(user[3], ban[3]):
                            self.printban(user, chan, borig, True, type)
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
                            self.printban(user, chan, ban, True, type)
                    elif "$a" in ban:
                        extban = ban.split(':')[1]
                        if self.globmatch(user[4], extban):
                            self.printban(user, chan, ban, True, type)

    def printban(self, user, chan, ban, ext, type):
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

        if type == "b":
            self.PutModule("\x02{}\x02 (account: {}, GECOS: {}) \x02banned\x02 in \x02{}\x02 with ban \x02{}\x02.".format(userban, account, user[3], chan, ban))
        elif type == "q":
            self.PutModule("\x02{}\x02 (account: {}, GECOS: {}) \x02quieted\x02 in \x02{}\x02 with quiet \x02{}\x02.".format(userban, account, user[3], chan, ban))
        elif type == "e":
            self.PutModule("\x02{}\x02 (account: {}, GECOS: {}) \x02excepted\x02 in \x02{}\x02 with exception \x02{}\x02.".format(userban, account, user[3], chan, ban))

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
        help = znc.CTable(250)
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
