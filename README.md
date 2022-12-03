# Firefox-History-Combiner

### Unfortunately, this project is in stasis for the time being. 
***I have ongoing personal matters to deal with and do not have the time to dedicate to this project.*** <br />
***I hope to be able to continue in the future. I will update if / when things change.*** <br />
<br />
<br />
A GUI tool to combine multiple Firefox history databases together! <br />
Most crucially, this program can combine DBs from (or indeed into) ***Firefox 3.0 onwards.*** <br />
This means that any Firefox history DB can be ***upgraded*** or ***downgraded*** to whatever version of Firefox you are using! <br />

The same holds true for Firefox forks such as Waterfox, Palemoon etc. They use the same data format for their history DBs. <br />

**But a word of caution:** <br />
I have **not** tested combining from/to Firefox forks thoroughly as of yet. Looking at the source code it seems <br />
like such DBs should behave as if they're Firefox DBs. It is possible this is not the case. <br />
If there are problems, make an [issue](https://github.com/JoshCode94/Firefox-History-Combiner/issues/new) and let me know.

### *Please note that this program is incomplete right now.*
The primary functionalities are all working but the workflow is a bit clunky. <br />

Also, while I have tested as thoroughly as I can (combining together DBs from multiple Firefox versions), anomolies are possible. <br />
You ***MUST*** make a backup of your main DB. It is so important. Not meaning to sound patronising, but please do. <br />
If there are any issues with my program, your main DB will not be affected if you follow this step.

You only need to backup your main DB. Any other DBs you're combining history data ***from*** are unaffected.


**Major features still missing are:**
- Auto-backup
- Detailed progress bar inside UI (replacing command prompt output)
- Documentation / a more fleshed-out Readme
- Lots more tweaks and extras I have in mind
- Support for multiple OSs
- An actual executable release of the main program (only **"Removing duplicate history entries"** is released right now)
