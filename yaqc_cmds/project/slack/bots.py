# Slack implementation for yaqc_cmds

import sys
import time

import pathlib
import appdirs
import toml

from slacker.__init__ import Slacker
from .rtmbot import RtmBot

config = toml.load(pathlib.Path(appdirs.user_config_dir("yaqc-cmds", "yaqc-cmds")) / "config.toml")
default_channel = config["slack"]["channel"]
witch_token = config["slack"]["token"]


class Bot(object):
    def __init__(self, token):
        self.slacker = Slacker(token)
        self.rtmbot = RtmBot(token)
        self.rtmbot.connect()
        # These values should be read from an ini file.
        self.channel = default_channel
        self.last_ping = 0
        try:
            self.check = self._check_channel()
        except:
            print("Something is seriously wrong with the called slackerbot. DO NOT USE THIS BOT!!")
        # try:
        if not self.check:
            print("The default channel does not exist. Better fix that.")
            self.channel = None
        else:
            # self.users.set_active()
            hello = []
            while hello == []:
                hello = self.rtmbot.rtm_read()
                time.sleep(0.01)

    def _check_channel(self, channel=None):
        if not channel:
            channel = self.channel
        try:
            self.slacker.channels.info(channel)
            return True
        except:
            return False

    def _filter_messages(self, messages):
        mess = []
        for i in messages:
            if "type" in i:
                if i["type"] == "message":
                    pm = i["channel"].startswith("D")
                    if i.get("text", "").startswith("<@U0EALA010>"):
                        i["text"] = i["text"].split(">", 1)[1]
                        mess.append(i)
                    elif pm:
                        mess.append(i)
        return mess

    def get_messages(self, newer_than=60):
        """
        Gets messages, returns [[message,timestamp,channel,user],..]. All elements are str.
        The messages are only returned if they start with a mention of witch followed by a space.
        """
        messages = []
        m = self.rtmbot.rtm_read()
        while not m == []:
            messages.extend(m)
            m = self.rtmbot.rtm_read()
        messages = self._filter_messages(messages)
        return messages

    def send_message(self, text, channel=None, attachments=[]):
        """
        text: string to post.
        attachemnts: list of attachment dictionaries, see slack api for more info.
        file_paths: a list of the file paths of the files to attache.
        Returns a True if message post was successful, returns False otherwise.
        """
        if channel is None:
            channel = self.channel
        if self._check_channel(channel):
            channel_object = self.rtmbot.slack_client.server.channels.find(channel)
            try:
                if attachments == []:
                    message = text.encode("ascii", "ignore")
                    channel_object.send_message("{}".format(text))
                else:
                    self.slacker.chat.post_message(
                        channel, text, attachments=attachments, as_user=True
                    )
                return True
            except:
                print(
                    "Message not posted: chat.post_message gave an error. Sorry buddy. :",
                    sys.exc_info()[0],
                )
                return False

    def upload_file(self, file_path, Title=None, first_comment=None, channel=None):
        """
        Uploads a file. Pretty self explanitory.
        """
        if channel is None:
            channel = self.channel
        if self._check_channel(channel):
            upload_ok = self.slacker.files.upload(
                file_path,
                title=Title,
                initial_comment=first_comment,
                channels=[channel],
            ).body["ok"]
            return upload_ok
        else:
            print("File not uploaded: Channel.info gave an error. Sorry bucko.")
            return False

    def delete_files(self):
        """
        Deletes files older than 90 days, then deletes old files unitl there is 1 GB space remaining.
        Returns the total space used if it all comes out ok and False otherwise.
        """
        old = time.time() + 90 * 24 * 60 * 60
        file_ask = self.slacker.files.list(ts_to=old).body
        if file_ask["ok"]:
            old = file_ask["files"]
            # it will try 3 times to remove each file, then give up if it hasn't finished.
            for i in range(3):
                for f in old:
                    if not f["is_starred"]:
                        if self.slacker.files.delete(f["id"]).body["ok"]:
                            old.remove(f)
            fl_info = self.slacker.files.list(count=1000).body
            all_files = fl_info["files"]
            for idx in range(fl_info["paging"]["pages"] - 1):
                all_files.extend(
                    self.slacker.files.list(ts_to=all_files[-1]["created"], count=1000)["files"][
                        1:
                    ]
                )
            space_used = sum([f["size"] for f in all_files])
            if space_used > 4 * 10 ^ 9:
                to_del = []
                idx = -1
                while space_used > 4 * 10 ^ 9:
                    if not all_files[idx]["is_starred"]:
                        to_del.append(all_files[idx]["id"])
                        space_used = space_used - all_files[idx]["size"]
                        idx = idx - 1
                for i in range(3):
                    for f in to_del:
                        if self.slacker.files.delete(f).body["ok"]:
                            to_del.remove(f)
            if to_del:
                return False
            else:
                return space_used
        else:
            return False

    def sign_off(self):
        "Use to signal that yaqc_cmds is shutting down."
        self.send_message("Picosecond system signing off.")


witch = Bot(witch_token)
"""
g = []
for i in range(100):
    g.extend(witch.get_messages())
    witch.rtmbot.autoping()
    time.sleep(.5)
"""
