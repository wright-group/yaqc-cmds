import time

import yaqc_cmds.project.slack.bots as bots

channel = "C0DD6BG9L"

ctrl = bots.witch


imageid = "0B8z-JGr_8g4RSlNPMC04bVBSZUk"
url = "https://drive.google.com/open?id=0B8z-JGr_8g4RdTN4SHdxVGZTSkE"
image_url = "https://docs.google.com/uc?id=" + imageid

field0 = {}
field0["title"] = "MOTORTUNE [w1, w1_Mixer_2, wm] 2016.02.02 16_03_57"
field0["title_link"] = url
field0["image_url"] = image_url

ctrl.send_message("scan complete - 00:09:51 elapsed", channel, attachments=[field0])
