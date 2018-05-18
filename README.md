# zncscripts
Scripts and modules and modifications for ZNC  [https://znc.in](https://znc.in "ZNC Homepage")

bansearch.py
------------
Quickly determine why a user is unable to join/talk in a channel.

Note that this script was optimized for freenode with the modes and extbans available there. 
It might not work or require additional tweaking for other networks.
Please also note that it is far from perfect and might fail in (constructed) edge cases, 
but for general consumption it should be fine.

This script takes a nick and channel as an argument, the nick has to be online.
The channel is then, per default, checked for +b (bans), +q (quiets) 
and $x, $a and $j [extbans](https://freenode.net/kb/answer/extbans "freenode kb entry on extbans")
Note that the $j behaviour is more accurate than other solutions, but not fully accurate, 
as the $j channel will be tested for all modes, not only +b. If someone feels bored enough to fix that: 
pull requests welcome.
Modes (currently supported: +b, +q, +e) can be specified as an optional third argument.

It will also check for the special cases of +q $~a (quiet unidentified users) and +r 
(registered users only channel mode)

The script can be loaded if your znc has python module support with the usual loadmod command, 
i.e. `/msg *status loadmod bansearch` if placed in a znc mod directory.

Example usage: 

`/msg *bansearch check Fuchs #freenode`
check if there are any bans or $a,$x,$j extbans or quiets matching the user Fuchs in #freenode

`/msg *bansearch check Fuchs #freenode be`
check if there are any bans or $a,$x,$j extbans or exempts (+e) matching the user Fuchs in #freenode

`/msg *bansearch check Fuchs #freenode q`
check if there are any quiets matching the user Fuchs in #freenode

Example output: 


```
/whois Testvieh
‎[Whois]‎ Testvieh is 01020304@gateway/web/cgi-irc/kiwiirc.com/ip.1.2.3.4 ([https://kiwiirc.com] Development release)
‎[Whois]‎ Testvieh is online via barjavel.freenode.net (Paris, FR, EU).
‎[Whois]‎ Testvieh is using a secure connection.
[Whois] Testvieh is logged in as Fuchs.
‎‎[Whois]‎ End of WHOIS list.


/msg *bansearch check Testvieh ##programming
‎<‎*bansearch‎>‎ Checking for bans on testvieh in ##programming-bans2 as well due to $j
<‎*bansearch‎>‎ Checking for bans on testvieh in ##bans as well due to $j
‎<‎*bansearch‎>‎ Checking for bans on testvieh in ##programming-bans as well due to $j
‎<‎*bansearch‎>‎ 01020304@gateway/web/cgi-irc/kiwiirc.com/ip.1.2.3.4  (account: Fuchs, GECOS: //kiwiirc.com] development release) banned in ##programming with ban *!*@gateway/web/cgi-irc/*.
‎<‎*bansearch‎>‎ Ban check complete.
```
