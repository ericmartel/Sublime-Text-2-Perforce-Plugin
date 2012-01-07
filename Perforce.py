# Written by Eric Martel (emartel@gmail.com / www.ericmartel.com)
# Inspired by https://gist.github.com/1065808

# to add a keyboard shortcut, call perforce_checkout

import sublime
import sublime_plugin

import os
import stat
import subprocess

warningsenabled = False;

def Checkout(in_filename):
    filestats = os.stat(in_filename)[0];
    if(filestats & stat.S_IWRITE):
        return -1, "File is already writable."

    folder_name, filename = os.path.split(in_filename)

    # check if the file is in the depot
    command = 'p4 info'
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=folder_name, shell=True)
    result, err = p.communicate()

    if(err):
        return 0, err.strip()
    
    # locate the line containing "Client root: " and extract the following path
    startindex = result.find("Client root: ")
    if(startindex == -1):
        return -1, "Unexpected output from 'p4 info'."

    startindex += 13 # advance after 'Client root: '
    endindex = result.find("\n", startindex)
    if(endindex == -1):
        return -1, "Unexpected output from 'p4 info'."

    clientroot = result[startindex:endindex].strip()
    clientrootindex = folder_name.lower().find(clientroot.lower());
    
    if(clientrootindex == -1):
        return -1, "File is not under client's root " + clientroot
    
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
        if(view.is_dirty()):
            success, message = Checkout(view.file_name())
            if(success >= 0):
                print "Perforce:", message
            else:
                if(warningsenabled):
                    print "Perforce [warning]:", message

class PerforceCheckoutCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if(self.view.file_name()):
            success, message = Checkout(self.view.file_name())
            if(success >= 0):
                print "Perforce:", message
            else:
                if(warningsenabled):
                    print "Perforce [warning]:", message