# Written by Eric Martel (emartel@gmail.com / www.ericmartel.com)
# Inspired by https://gist.github.com/1065808

# to add a keyboard shortcut, call perforce_add or perforce_checkout

import sublime
import sublime_plugin

import os
import stat
import subprocess

# Plugin Settings
# perforce_warnings_enabled # will output messages when warnings happen
# perforce_auto_checkout # when true, any file within the client spec will be checked out when saving if read only   
# perforce_auto_add # when true, any file within the client spec that doesn't exist during the presave will be added

# Utility functions
def IsFolderUnderClientRoot(in_folder):
    # check if the file is in the depot
    command = 'p4 info'
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=in_folder, shell=True)
    result, err = p.communicate()

    if(err):
        return -1, err.strip()
    
    # locate the line containing "Client root: " and extract the following path
    startindex = result.find("Client root: ")
    if(startindex == -1):
        return -1, "Unexpected output from 'p4 info'."

    startindex += 13 # advance after 'Client root: '
    endindex = result.find("\n", startindex)
    if(endindex == -1):
        return -1, "Unexpected output from 'p4 info'."

    clientroot = result[startindex:endindex].strip()
    clientrootindex = in_folder.lower().find(clientroot.lower());

    if(clientrootindex == -1):
        return 0

    return 1


def IsFileInDepot(in_folder, in_filename):
    isUnderClientRoot = IsFolderUnderClientRoot(in_folder);
    if(os.path.isfile(os.path.join(in_folder, in_filename))): # file exists on disk, not being added
        if(isUnderClientRoot):
            return 1
        else:
            return 0
    else:
        if(isUnderClientRoot):
            return -1 # will be in the depot, it's being added
        else:
            return 0

# Checkout section
def Checkout(in_filename):
    folder_name, filename = os.path.split(in_filename)
    isInDepot = IsFileInDepot(folder_name, filename)
    if(isInDepot != 1):
        return -1, "File is not under the client root."
    
    filestats = os.stat(in_filename)[0];
    if(filestats & stat.S_IWRITE):
        return -1, "File is already writable."

    # check out the file
    command = 'p4 edit ' + filename
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=folder_name, shell=True)
    result, err = p.communicate()

    if(not err):
        return 1, result.strip()
    else:
        return 0, err.strip()
  
class PerforceAutoCheckout(sublime_plugin.EventListener):  
    def on_pre_save(self, view):
        # check if this part of the plugin is enabled
        if(not view.settings().get('perforce_auto_checkout', True)):
            if(view.settings().get('perforce_warnings_enabled', False)):
                print "Perforce [warning]: Auto Checkout disabled"
            return
              
        if(view.is_dirty()):
            success, message = Checkout(view.file_name())
            if(success >= 0):
                print "Perforce:", message
            else:
                if(view.settings().get('perforce_warnings_enabled', False)):
                    print "Perforce [warning]:", message

class PerforceCheckoutCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if(self.view.file_name()):
            success, message = Checkout(self.view.file_name())
            if(success >= 0):
                print "Perforce:", message
            else:
                if(view.settings().get('perforce_warnings_enabled', False)):
                    print "Perforce [warning]:", message

# Add section
def Add(in_folder, in_filename):
    # check out the file
    command = 'p4 add ' + in_filename
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=in_folder, shell=True)
    result, err = p.communicate()

    if(not err):
        return 1, result.strip()
    else:
        return 0, err.strip()

class PerforceAutoAdd(sublime_plugin.EventListener):
    preSaveIsFileInDepot = 0
    def on_pre_save(self, view):
        self.preSaveIsFileInDepot = 0

        # check if this part of the plugin is enabled
        if(not view.settings().get('perforce_auto_add', True)):
            if(view.settings().get('perforce_warnings_enabled', False)):
                print "Perforce [warning]: Auto Add disabled"
            return

        folder_name, filename = os.path.split(view.file_name())
        self.preSaveIsFileInDepot = IsFileInDepot(folder_name, filename)

    def on_post_save(self, view):
        if(self.preSaveIsFileInDepot == -1):
            folder_name, filename = os.path.split(view.file_name())
            success, message = Add(folder_name, filename)
        

class PerforceAddCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if(self.view.file_name()):
            folder_name, filename = os.path.split(self.view.file_name())

            if(IsFileInDepot(folder_name, filename)):
                success, message = Add(folder_name, filename)
            else:
                success = 0
                message = "File is not under the client root."

            if(success >= 0):
                print "Perforce:", message
            else:
                if(view.settings().get('perforce_warnings_enabled', False)):
                    print "Perforce [warning]:", message
