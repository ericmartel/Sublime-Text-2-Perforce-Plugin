# Inspired by https://gist.github.com/1065808

import sublime
import sublime_plugin

import os
import stat
import subprocess

def Checkout(filename):
    filestats = os.stat(filename)[0];
    if(filestats & stat.S_IWRITE):
        return -1, "File is already writable."
    
    folder_name, filename = os.path.split(filename);
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
            success, message = Checkout(view.file_name());
            if(success >= 0):
                print "Perforce:", message;

class PerforceCheckoutCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if(self.view.file_name()):
            success, message = Checkout(self.view.file_name());
            if(success >= 0):
                print "Perforce:", message;
