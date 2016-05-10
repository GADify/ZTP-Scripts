#!/usr/bin/python

# Dynamically configure base config of all Advanced Lab switches
# based on remote interface number on the Core switch. Used with ZTP
# In this lab, each Student switch is connected to the same-numbered
# Interface on the Core switch. Student-1: Eth1, Student-5: Eth5, etc.
# By retrieving this info, all IP addresses and the hostname can be 
# Dynamically configured

# Written Dec 5, 2013 by Gary A. Donahue

from string import Template
import subprocess
import string 
import sys
import time
import re

#-- LLDP Discovery Code --#
# This chunk of code retrieves the Ethernet interface on the remote
# Switch attached to our interface Ma1.

# Check each line, looking for the one that contains Ma1, 
# but only in the first 5 chars of the line. This should 
# keep remote Ma1s from triggering. 

# GAD 9-10-15: Note that LLDP sends every 30 seconds by default. If the switch
#     boots in less than 30 seconds, the 'show lldp nei' may not get an Ma1
#     response which would cause a traceback. I've rewritten it after much 
#     debugging and hair-pulling so that it retries until it gets an answer. 

LLDPLines = ""
IntNum = "xx"
LoopCounter = 0
while IntNum == "xx":
   LLDPLines = ""
   LLDP = subprocess.Popen(["/usr/bin/FastCli", "-c", "sho lldp nei"], stdout=subprocess.PIPE)
   for Line in iter(LLDP.stdout.readline, ''):
      LLDPLines = LLDPLines + Line
      if Line.count("Ma1", 0, 5):
         Fields = Line.split()
         # [0] - Local Int (Should be Ma1 on match)
         # [1] - Remote Device
         # [2] - Remote Device's Interface
         # [3] - TTL
   
         # Strip out the non-numerics using Regex
         IntNum = re.sub("[^0-9]", "", Fields[2])
         subprocess.Popen(["/usr/bin/logger", 
                           "-p", "local4.crit", 
                           "-t", "ZTP: ", 
                           "Interface found: ", IntNum])
   if IntNum == "xx":
      # No LLDP was seen on Ma1! probably because LLDP hasn't started yet. 
      # So loop a few times using incremental backoff.
      LoopCounter +=1
      # The following 'logger' stuff will print an error on the console - neat!
      subprocess.Popen(["/usr/bin/logger", 
                        "-p", "local4.crit", 
                        "-t", "ZTP: ", 
                        "LLDP try number ", 
                        str(LoopCounter),
                        " Failed - trying again in ", str(LoopCounter) , " seconds."])
      time.sleep(LoopCounter)
      if LoopCounter > 4:
         subprocess.Popen(["/usr/bin/logger", 
                           "-p", "local4.crit", 
                           "-t", "ZTP: ", 
                           "Too many failures - aborting."])
         IntNum = "failed"

if IntNum == "failed":
      # Why did we not get an int?
      subprocess.Popen(["/usr/bin/logger", 
                        "-p", "local4.crit", 
                        "-t", "ZTP: ", 
                        "[ WARNING! ]  LLDP Request failed. Output written to flash"])

      InfoDump = "Show LLDP Neighbor\n----------------\n"
      InfoDump += LLDPLines
      ts = str(int(time.time()))
      FileName = "/mnt/flash/Output-" + ts
      OutputFile = open(FileName, 'w')
      OutputFile.write( InfoDump )
      OutputFile.close()

## Special cases for Spine and DANZ switches
## Don't bother trying wget - it doesn't work for some reason. 

## These are forcing behavior based on specific ports

if IntNum == "41":
   # Spine-1
   GetConfig  = subprocess.Popen(["Cli" , 
                                  "-p15" , 
                                  "-c" , 
                                  "copy http://10.0.0.100/ZTP/CONFIGS/Spine-1/startup-config flash:"] , 
                                  stdout=subprocess.PIPE)
elif IntNum == "42":
   # Spine-2
   GetConfig  = subprocess.Popen(["Cli" , 
                                  "-p15" , 
                                  "-c" , 
                                  "copy http://10.0.0.100/ZTP/CONFIGS/Spine-2/startup-config flash:"] , 
                                  stdout=subprocess.PIPE)
elif IntNum == "43":
   # DANZ-1
   GetConfig  = subprocess.Popen(["Cli" , 
                                  "-p15" , 
                                  "-c" , 
                                  "copy http://10.0.0.100/ZTP/CONFIGS/DANZ-1/startup-config flash:"] , 
                                  stdout=subprocess.PIPE)
elif IntNum == "44":
   # DANZ-2
   GetConfig  = subprocess.Popen(["Cli" , 
                                  "-p15" , 
                                  "-c" , 
                                  "copy http://10.0.0.100/ZTP/CONFIGS/DANZ-2/startup-config flash:"] , 
                                  stdout=subprocess.PIPE)
else:
   ## If not a special case, then this is a Student Switch
   IntNumPadded = IntNum.zfill(2)
   
   # Output is squelched during ZTP, so printing has no value
   #print "Switch number: " + IntNum
   #print "Switch number: " + IntNumPadded
   
   # -- End of LLDP Discover Code --#
  

## For some reason, the "management api http-commands" section doesn't load 
## all the time
## It **seems** to be switches 2, 13, 15 and 16. Why? 
## 
## Figure this out and I'll buy you lunch. Not a very nice lunch, but lunch. 

 
   # -- Begin Template Code --#
   Replacements = {       "Number": IntNum, 
                    "NumberPadded": IntNumPadded }
   
   Config = Template("""
! Default ZTP-created config
!
alias conint sh interface | i connected
alias senz show interface counter error | nz
alias shmc show int | awk '/^[A-Z]/ { intf = $1 } /, address is/ { print intf, $6 }'
alias snz show interface counter | nz
alias spd show port-channel %1 detail all
alias sqnz show interface counter queue | nz
alias srnz show interface counter rate | nz
alias intdesc
   !! Usage: intdesc interface-name description
   10 config
   20 int %1
   30 desc %2
   40 exit
!
hostname Student-$NumberPadded
!
aaa authentication policy local allow-nopassword-remote-login
!
username Script secret Arista
!
interface Ethernet1
   description [ ESXi ]
!
interface Ethernet2
   description [ Agile Port ]
   shutdown
!
interface Ethernet4
   description [ Subsumed Port ]
   shutdown
!
interface Ethernet6
   description [ Subsumed Port ]
   shutdown
!
interface Ethernet8
   description [ Subsumed Port ]
   shutdown
!
interface Ethernet19
   description [ DANZ-1 ]
!
interface Ethernet20
   description [ DANZ-2 ]
!
interface Ethernet21
   description [ Spine-1 ]
!
interface Ethernet22
   description [ Spine-2 ]
!
interface Ethernet23
   description [ MLAG Peer ]
!
interface Ethernet24
   description [ MLAG Peer ]
!
interface Management1
   ip address 10.0.0.$Number/24
!
management api http-commands
   no shutdown
!
banner login
+---------------------------------------+
| Switch:  Student-$NumberPadded                   |
|                                       |
| Purpose: Training Lab A (alab)        | 
| Owner:   Training Dept.               |
| Email:   training-team@arista.com     |
+---------------------------------------+
EOF
!
end
   """).safe_substitute(Replacements)
   
   
   # -- Write Config to flash:startup-config via Linux -- #
   
   ConfigFile = open('/mnt/flash/startup-config', 'w')
   ConfigFile.write( Config )
   ConfigFile.close()
     
sys.exit( 0 )
