# Licensed under the MIT license, see https://github.com/Fuchs/zncscripts/blob/master/LICENSE
# Based on the work of and cooperation with MuffinMedic, https://github.com/MuffinMedic

import znc
import fnmatch
import re
import time
from datetime import datetime

class bansearch(znc.Module):

    module_types = [znc.CModInfo.NetworkModule]

    def OnLoad(self, args, message):
        self.loadSettings()
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
                    return znc.HALTCORE
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
            setter = message[5]
            stamp = message[6]
        elif type == "q":
            ban = message[5]
            setter = message[6]
            stamp = message[7]

        if IsEnd:
            self.check(IsEnd, channel, None, type, None, None)
        elif not ban.startswith('$'):
            nuh = self.splitircban(ban)
            self.check(IsEnd, channel, nuh, type, stamp, setter)
        elif "$" in ban:
            self.check(IsEnd, channel, ban, type, stamp, setter)

    def check(self, IsEnd, chan, ban, type, stamp, setter):
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
                        self.printban(user, chan, ban, False, type, stamp, setter)
                else:
                    if "$x" in ban:
                        borig = ban
                        ban = self.splitircuser(ban)
                        if self.globmatch(user[0], ban[0]) and self.globmatch(user[1], ban[1]) and self.globmatch(user[2], ban[2]) and self.globmatch(user[3], ban[3]):
                            self.printban(user, chan, borig, True, type, stamp, setter)
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
                            self.printban(user, chan, ban, True, type, stamp, setter)
                    elif "$a" in ban:
                        extban = ban.split(':')[1]
                        if self.globmatch(user[4], extban):
                            self.printban(user, chan, ban, True, type, stamp, setter)

    def formatTimestamp(self, when):
        ts = int(when)
        return datetime.utcfromtimestamp(ts).strftime(self.timeStampFormat)
        
    def formatAgo(self, when):
        now = time.time()
        elapsed = int(now) - int(when)

        # minutes
        elapsed = elapsed // 60

        if elapsed < 1:
            return "(a few seconds ago)"
        if elapsed == 1:
            return "(1 minute ago)"
        if elapsed < 60:
            return "(" + str(elapsed) + " minutes ago)"

        # hours
        elapsed = elapsed // 60
        if elapsed == 1:
            return "(1 hour ago)"
        if elapsed < 24:
            return "(" + str(elapsed) + " hours ago)"

        #days
        elapsed = elapsed // 24
        if elapsed == 1:
            return "1 day"
        return "(" + str(elapsed) + " days ago)"

    def printban(self, user, chan, ban, ext, type, stamp, setter):
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

        ssetter = ""
        if self.showSetter:
            ssetter = " by \x02" + setter + "\x02"

        tstamp = ""
        if self.showTimeStamp:
            tstamp = " at \x02" + self.formatTimestamp(stamp) + "\x02"

        ago = ""
        if self.showTimeAgo:
            ago = " \x02" + self.formatAgo(stamp) + "\x02"

        if type == "b":
            self.PutModule("\x02{}\x02 (account: {}, GECOS: {}) \x02banned\x02 in \x02{}\x02 with \x02{}\x02{}{}{}.".format(userban, account, user[3], chan, ban, ssetter, tstamp, ago))
        elif type == "q":
            self.PutModule("\x02{}\x02 (account: {}, GECOS: {}) \x02quieted\x02 in \x02{}\x02 with \x02{}\x02{}{}{}.".format(userban, account, user[3], chan, ban, ssetter, tstamp, ago))
        elif type == "e":
            self.PutModule("\x02{}\x02 (account: {}, GECOS: {}) \x02excepted\x02 in \x02{}\x02 with \x02{}\x02{}{}{}.".format(userban, account, user[3], chan, ban, ssetter, tstamp, ago))

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
        self.quietsDone = {}
        self.bansDone = {}
        self.exceptsDone = {}
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
        elif commands[0] == "set":
            key = None
            value = None
            if len(commands) > 1:
                key = commands[1] 
            if len(commands) > 2: 
                value = commands[2]
            ret = self.setSetting(key, value)
            self.PutModule(ret)
            self.loadSettings()
        elif commands[0] == "settings":
            self.showSettings()
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
        help.SetCell("Command", "set")
        help.SetCell("Arguments", "<key> <value>")
        help.SetCell("Description", "Sets settings, for available settings and their values see \"settings\"")
        help.AddRow()
        help.SetCell("Command", "settings")
        help.SetCell("Arguments", "")
        help.SetCell("Description", "Displays settings and their value")
        help.AddRow()
        help.SetCell("Command", "help")
        help.SetCell("Arguments", "")
        help.SetCell("Description", "Display this output")

        self.PutModule(help)

    def setSetting(self, key, value=None):
        if not key or not value: 
            self.PutModule("Syntax: set <key> <value>, e.g. set showTimestamp True")
        key = key.lower()
        if key in ("showsetter", "showtimeago", "showtimestamp"): 
            if value and self.getBool(value):
                self.nv[key] = "True"
                return "\x02{option}\x02 value set to \x02{setting}\x02".format(option=key, setting="True")
            elif value and not self.getBool(value):
                self.nv[key] = "False"
                return "\x02{option}\x02 value set to \x02{setting}\x02".format(option=key, setting="False")
        elif key == "timeStampFormat":
            ts = int("3152435682")
            try:
                datetime.utcfromtimestamp(ts).strftime(value)
                self.nv[key] = value
                return "{option} option set to \x02{setting}\x02".format(option=key, setting=value)
            except:
                return "Timestamp format not accepted, check for syntax errors"
        else:
            return "Invalid option. Options are 'showsetter', 'showtimeago', 'showtimestamp' and 'timestampformat'."
    
    def showSettings(self):
        settings = znc.CTable()
        settings.AddColumn("Setting")
        settings.AddColumn("Value")
        settings.AddColumn("Description")
        settings.AddRow()
        settings.SetCell("Setting", "showSetter")
        settings.SetCell("Value", str(self.showSetter))
        settings.SetCell("Description", "Show who did set that mode, values are True or False.")
        settings.AddRow()
        settings.SetCell("Setting", "showTimeAgo")
        settings.SetCell("Value", str(self.showTimeAgo))
        settings.SetCell("Description", "Show how long since the mode has been set, values are True or False.")
        settings.AddRow()
        settings.SetCell("Setting", "showTimestamp")
        settings.SetCell("Value", str(self.showTimeStamp))
        settings.SetCell("Description", "Show the time and date at which the mode was set, values are True or False.")
        settings.AddRow()
        settings.SetCell("Setting", "TimestampFormat")
        settings.SetCell("Value", str(self.timeStampFormat))
        settings.SetCell("Description", "Format for the timestamp of \"showtimestamp\", values are valid strftime formattings.")
        self.PutModule(settings)
    
    def loadSettings(self):
        try: 
            if 'showsetter' in self.nv:
                self.showSetter = self.getBool(self.nv['showsetter'])
            else:
                self.showSetter = False
                self.nv['showsetter'] = "False"
            if 'showtimeago' in self.nv:
                self.showTimeAgo = self.getBool(self.nv['showtimeago'])
            else:
                self.showTimeAgo = False
                self.nv['showtimeago'] = "False"
            if 'showtimestamp' in self.nv:
                self.showTimeStamp = self.getBool(self.nv['showtimestamp'])
            else:
                self.showTimeStamp = False
                self.nv['showtimestamp'] = "False"
            if 'timestampformat' in self.nv:
                self.timeStampFormat = self.nv['timestampformat']
            else:
                self.timeStampFormat = '%Y-%m-%d %H:%M:%S'
                self.nv['timeStampFormat'] = '%Y-%m-%d %H:%M:%S'
        except Exception as e:
            self.PutModule("Loading settings failed, check your config. Error: %s" % e)

    def getBool(self, bString):
        return bString.lower() in ("true", "yes", "on", "1")


    def globmatch(self, string, compare):
        escaped = self.globpattern.sub("[\g<1>]", compare)
        return fnmatch.fnmatch(string, escaped)

