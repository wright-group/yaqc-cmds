#Slacker implementation for pyCMDS


import os
import sys
import time
import glob
import datetime

from PyQt4 import QtGui, QtCore

import project.classes as pc
import project.logging_handler as logging_handler
import project.project_globals as g
from project.ini_handler import Ini
import bots
main_dir = g.main_dir.read()
ini = Ini(os.path.join(main_dir, 'project', 'slack', 'bots.ini'))
#import daq.daq as daq

import WrightTools as wt


### container objects #########################################################


class Messages(QtCore.QMutex):

    def __init__(self):
        '''
        holds list of enqueued options
        '''
        QtCore.QMutex.__init__(self)
        self.value = []

    def read(self):
        self.lock()
        out = self.value
        self.value = []
        self.unlock()
        return out

    def push(self, value):
        self.lock()
        self.value.append(value)
        self.unlock()

    def pop(self):
        self.lock()
        self.value = self.value[1:]
        self.unlock()
        
messages_mutex = Messages()

        
### address & control objects #################################################


class Address(QtCore.QObject):
    queue_emptied = QtCore.pyqtSignal()

    def __init__(self, busy, enqueued):
        QtCore.QObject.__init__(self)
        self.busy = busy
        self.enqueued = enqueued
        self.ctrl = bots.witch

    @QtCore.pyqtSlot(str, list)
    def dequeue(self, method, inputs):
        # execute method
        getattr(self, str(method))(inputs)  # method passed as qstring
        # remove method from enqueued
        self.enqueued.pop()
        if not self.enqueued.read():
            self.ctrl.rtmbot.autoping()
            self.queue_emptied.emit()
            self.busy.write(False)
            
    def get_messages(self, inputs):
        newer_than = inputs[0]
        messages = self.ctrl.get_messages(newer_than=newer_than)
        for message in messages:
            messages_mutex.push(message)
            
    def send_message(self, inputs):
        text, channel, attachments = inputs
        self.ctrl.send_message(text, channel, attachments)
        
    def upload_file(self, inputs):
        file_path, Title, first_comment, channel = inputs
        self.ctrl.upload_file(file_path, Title, first_comment, channel)
        
    def delete_files(self, inputs):
        self.ctrl.delete_files
        
    def sign_off(self, inputs):
        message = inputs[0]
        self.ctrl.send_message(message)


class Control:
    
    def __init__(self):
        self.most_recent_delete = time.time()
        # create control containers
        self.busy = pc.Busy()
        self.enqueued = pc.Enqueued()
        # create address object
        self.thread = QtCore.QThread()
        self.address = Address(self.busy, self.enqueued)
        self.address.moveToThread(self.thread)
        self.thread.start()
        # create q
        self.q = pc.Q(self.enqueued, self.busy, self.address)
        # connect
        g.shutdown.add_method(self.close)
        # signal startup
        self.send_message('signing on', ini.read('bots', 'channel'))
        g.slack_control.write(self)
        
    def _get_data_folders(self, full=False):
        data_directory = os.path.join(g.main_dir.read(), 'data')
        if full:
            folder_names = [os.path.join(data_directory, name) for name in os.listdir(data_directory) if os.path.isdir(os.path.join(data_directory, name))]
        else:
            folder_names = [name for name in os.listdir(data_directory) if os.path.isdir(os.path.join(data_directory, name))]
        folder_names.reverse()  # most recent should be first
        return folder_names
        
    def _make_attachment(self, text, pretext=None, fields=None, color='#808080'):
        attachment = {}
        if pretext is not None:
            attachment['pretext'] = pretext
        if fields is not None:
            attachment['fields'] = fields
        attachment['color'] = color
        attachment['text'] = text
        attachment['mrkdwn_in'] = ['fields']
        return attachment
        
    def _make_field(self, title, value, short=False):
        field = {}
        field['title'] = title
        field['value'] = value
        field['short'] = short
        return field
        
    def _make_list(self, items):
        out = ''
        n = 0
        for item in items:
            out += str(n).zfill(2) + ' :arrow_right: ' + item + '\n'
            n+= 1
        return out
        
    def close(self):
        self.q.push('sign_off', ['signing off'])
        time.sleep(1)
        # quit thread
        self.thread.exit()
        self.thread.quit()
        
    def delete_files(self):
        self.q.push('delete_files')
        self.send_message('old files deleted :wastebasket:')
        
    def get(self, text, channel):
        # extract numbers from text
        numbers = [int(s) for s in text.split() if s.isdigit()]
        if len(numbers) > 0:
            number = numbers[0]
        else:
            number = 0
        # get data folder
        data_folder = self._get_data_folders(full=True)[number]
        print data_folder
        # get data filepath
        data_path = wt.kit.glob_handler('.data', data_folder)[0]
        self.upload_file(data_path, channel=channel)
        
    def log(self, text, channel):
        log_filepath = logging_handler.filepath
        print text
        if 'get' in text:
            print log_filepath
            self.upload_file(log_filepath, channel=channel)
            return
        # extract numbers from text
        numbers = [int(s) for s in text.split() if s.isdigit()]
        if len(numbers) > 0:
            number = numbers[0]
        else:
            number = 10
        # get log text
        with open(log_filepath) as f:
            lines = f.readlines()
        lines.reverse()
        num_lines = len(lines)
        if len(lines) < number:
            number = len(lines)
        lines = lines[:number]
        # send message
        list_string = self._make_list(lines)
        attachment = self._make_attachment(list_string) 
        self.send_message('here are the {0} most recent log items (out of {1})'.format(number, num_lines), channel, [attachment])
    
    def ls(self, text, channel):
        # extract numbers from text
        numbers = [int(s) for s in text.split() if s.isdigit()]
        if len(numbers) > 0:
            number = numbers[0]
        else:
            number = 10
        # get files
        folder_names = self._get_data_folders()
        if len(folder_names) == 0:
            self.send_message('PyCMDS currently has no data')
            return
        num_folders = len(folder_names)
        if len(folder_names) < number:
            number = len(folder_names)
        folder_names = folder_names[:number]
        # send message
        list_string = self._make_list(folder_names)
        attachment = self._make_attachment(list_string)
        self.send_message('here are the {0} most recent aquisitions (out of {1})'.format(number, num_folders), channel, [attachment])
        
    def poll(self):
        if not self.busy.read():
            self.q.push('get_messages', [60])
        self.read_messages()
        # call delete files if it is within 60 seconds of midnight
        if time.time() - self.most_recent_delete > 100:
            now = datetime.datetime.now()
            midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
            if (now - midnight).seconds < 60:
                self.delete_files()
                self.most_recent_delete = time.time()
            
    def read_messages(self):
        messages = messages_mutex.read()
        for message in messages:
            # only process messages
            if not 'type' in message.keys():
                continue
            if not message['type'] == 'message':
                continue        
            # unpack some things
            text = message['text']
            channel = message['channel']
            # only process messages that are posted in the appropriate channel
            if not channel == ini.read('bots', 'channel'):
                continue
            # only process messages that start with '@witch'
            if not text.startswith('<@U0EALA010>'):
                continue
            else:
                text = text.split(' ', 1)[1]
                print 'message read from slack:', text
            # process
            if 'echo ' in text:
                out = text.split('echo ', 1)[1]
                self.send_message(out, channel)   
            elif 'log' in text:
                self.log(text, channel)
            elif 'get' == text[:3]:
                self.get(text, channel)
            elif 'ls' in text:
                self.ls(text, channel)
            elif 'status' in text:
                self.status(text, channel)
            elif 'help' in text:
                self.send_help(channel)
            elif text == 'delete':
                self.delete_files()
            else:
                attachment = self._make_attachment(text)
                self.send_message('command not recognized - type help for a list of available commands', channel, [attachment])

    def send_help(self, channel):
        command_fields = []
        command_fields.append(self._make_field('get [n=0]', 'Get the *nth* most recent data file.'))
        command_fields.append(self._make_field('ls [n=10]', 'List the *n* most recent aquisitions.'))
        command_fields.append(self._make_field('log [get or n=10]', '*get* the log file, or list the *n* most recent logged actions.'))
        command_fields.append(self._make_field('status', 'Get the current status of PyCMDS.'))
        attachment = self._make_attachment('', fields=command_fields)
        self.send_message('here are my commands :robot_face:', channel, [attachment])

    def send_message(self, text, channel=None, attachments=[]):
        self.q.push('send_message', [text, channel, attachments])
        
    def status(self, text, channel):
        if g.progress_bar.time_elapsed.text() == '00:00:00':
            self.send_message('no scan run since startup', channel)
        elif g.progress_bar.time_remaining.text() == '00:00:00':
            self.send_message('scan completed', channel)
        else:
            self.send_message('scan ongoing - {} remains'.format(g.progress_bar.time_remaining.text()), channel)
        
    def upload_file(self, file_path, title=None, first_comment=None, channel=None):
        self.q.push('upload_file', [file_path, title, first_comment, channel])

control = Control()
