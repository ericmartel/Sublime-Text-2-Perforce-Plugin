# Written by Eric Martel (emartel@gmail.com / www.ericmartel.com)
# Inspired by https://gist.github.com/1065808

# available keyboard shortcuts
#   perforce_add
#   perforce_checkout
#   perforce_revert
#   perforce_diff
#   perforce_graphical_diff_with_depot - uses p4diff for now

# changelog
# Eric Martel - first implementation of add / checkout
# Tomek Wytrebowicz & Eric Martel - handling of forward slashes in clientspec folder
# Rocco De Angelis & Eric Martel - first implementation of revert
# Eric Martel - first implementation of diff
# Eric Martel - first implementation of Graphical Diff from Depot

import sublime
import sublime_plugin

import os
import stat
import subprocess
import tempfile
import threading

# Plugin Settings are located in 'perforce.sublime-settings' make a copy in the User folder to keep changes

# Utility functions
def GetClientRoot():
    # check if the file is in the depot
    command = 'p4 info'
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=None, shell=True)
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

    # convert all paths to "os.sep" slashes 
    convertedclientroot = result[startindex:endindex].strip().lower().replace('\\', os.sep).replace('/', os.sep)

    return convertedclientroot

def IsFolderUnderClientRoot(in_folder):
    # check if the file is in the depot
    clientroot = GetClientRoot()

    # convert all paths to "os.sep" slashes 
    convertedfolder = in_folder.lower().replace('\\', os.sep).replace('/', os.sep);
    clientrootindex = convertedfolder.find(clientroot); 

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

def PerforceCommandOnFile(in_command, in_folder, in_filename):
    command = 'p4', in_command,  in_filename
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=in_folder, shell=True)
    result, err = p.communicate()

    if(not err):
        return 1, result.strip()
    else:
        return 0, err.strip()   

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
    return PerforceCommandOnFile("edit", folder_name, in_filename);
  
class PerforceAutoCheckout(sublime_plugin.EventListener):  
    def on_pre_save(self, view):
        perforce_settings = sublime.load_settings('Perforce.sublime-settings')

        # check if this part of the plugin is enabled
        if(not perforce_settings.get('perforce_auto_checkout')):
            if(perforce_settings.get('perforce_warnings_enabled')):
                print "Perforce [warning]: Auto Checkout disabled"
            return
              
        if(view.is_dirty()):
            success, message = Checkout(view.file_name())
            if(success >= 0):
                print "Perforce:", message
            else:
                if(perforce_settings.get('perforce_warnings_enabled')):
                    print "Perforce [warning]:", message

class PerforceCheckoutCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        perforce_settings = sublime.load_settings('Perforce.sublime-settings')

        if(self.view.file_name()):
            success, message = Checkout(self.view.file_name())
            if(success >= 0):
                print "Perforce:", message
            else:
                if(perforce_settings.get('perforce_warnings_enabled')):
                    print "Perforce [warning]:", message
        else:
            if perforce_settings.get('perforce_warnings_enabled'):
                print "Perforce [warning]: View does not contain a file"

# Add section
def Add(in_folder, in_filename):
    # add the file
    return PerforceCommandOnFile("add", in_folder, in_filename);

class PerforceAutoAdd(sublime_plugin.EventListener):
    preSaveIsFileInDepot = 0
    def on_pre_save(self, view):
        perforce_settings = sublime.load_settings('Perforce.sublime-settings')

        self.preSaveIsFileInDepot = 0

        # check if this part of the plugin is enabled
        if(not perforce_settings.get('perforce_auto_add')):
            if(perforce_settings.get('perforce_warnings_enabled')):
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
            perforce_settings = sublime.load_settings('Perforce.sublime-settings')
            folder_name, filename = os.path.split(self.view.file_name())

            if(IsFileInDepot(folder_name, filename)):
                success, message = Add(folder_name, filename)
            else:
                success = 0
                message = "File is not under the client root."

            if(success >= 0):
                print "Perforce:", message
            else:
                if(perforce_settings.get('perforce_warnings_enabled')):
                    print "Perforce [warning]:", message
        else:
            if perforce_settings.get('perforce_warnings_enabled'):
                print "Perforce [warning]: View does not contain a file"

# Revert section
def Revert(in_folder, in_filename):
    # revert the file
    return PerforceCommandOnFile("revert", in_folder, in_filename);

class PerforceRevertCommand(sublime_plugin.TextCommand):
    def run_(self, args): # revert cannot be called when an Edit object exists, manually handle the run routine
        if(self.view.file_name()):
            perforce_settings = sublime.load_settings('Perforce.sublime-settings')
            folder_name, filename = os.path.split(self.view.file_name())

            if(IsFileInDepot(folder_name, filename)):
                success, message = Revert(folder_name, filename)
                if(success): # the file was properly reverted, ask Sublime Text to refresh the view
                    self.view.run_command('revert');
            else:
                success = 0
                message = "File is not under the client root."

            if(success >= 0):
                print "Perforce:", message
            else:
                if(perforce_settings.get('perforce_warnings_enabled')):
                    print "Perforce [warning]:", message  
        else:
            if perforce_settings.get('perforce_warnings_enabled'):
                print "Perforce [warning]: View does not contain a file"      

# Diff section
def Diff(in_folder, in_filename):
    # diff the file
    return PerforceCommandOnFile("diff", in_folder, in_filename);

class PerforceDiffCommand(sublime_plugin.TextCommand):
    def run(self, edit): 
        if(self.view.file_name()):
            perforce_settings = sublime.load_settings('Perforce.sublime-settings')

            folder_name, filename = os.path.split(self.view.file_name())

            if(IsFileInDepot(folder_name, filename)):
                success, message = Diff(folder_name, filename)
            else:
                success = 0
                message = "File is not under the client root."

            if(success >= 0):
                print "Perforce:", message
            else:
                if(perforce_settings.get('perforce_warnings_enabled')):
                    print "Perforce [warning]:", message
        else:
            if perforce_settings.get('perforce_warnings_enabled'):
                print "Perforce [warning]: View does not contain a file"
                    
# Graphical Diff With Depot section
def GraphicalDiffWithDepot(self, in_folder, in_filename):
    perforce_settings = sublime.load_settings('Perforce.sublime-settings')

    success, content = PerforceCommandOnFile("print", in_folder, in_filename)
    if(not success):
        return 0, content

    # Create a temporary file to hold the depot version
    tmp_file = open(os.path.join(tempfile.gettempdir(), "depot"+in_filename), 'w')

    # Remove the first two lines of content
    linebyline = content.splitlines();
    content=perforce_settings.get('perforce_end_line_separator').join(linebyline[1:]);

    try:
        tmp_file.write(content)
    finally:
        tmp_file.close()

    # Launch P4Diff with both files and the same arguments P4Win passes it
    command = 'p4diff ' + tmp_file.name + ' ' + os.path.join(in_folder, in_filename) + " -l \"" + in_filename + " in depot\" -e -1 4"
    
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=in_folder, shell=True)
    result, err = p.communicate()

    # Clean up
    os.unlink(tmp_file.name);

    return -1, "Executing command " + command

class PerforceGraphicalDiffWithDepotCommand(sublime_plugin.TextCommand):
    def run(self, edit): 
        if(self.view.file_name()):
            perforce_settings = sublime.load_settings('Perforce.sublime-settings')

            folder_name, filename = os.path.split(self.view.file_name())

            if(IsFileInDepot(folder_name, filename)):
                success, message = GraphicalDiffWithDepot(self, folder_name, filename)
            else:
                success = 0
                message = "File is not under the client root."

            if(success >= 0):
                print "Perforce:", message
            else:
                if(perforce_settings.get('perforce_warnings_enabled')):
                    print "Perforce [warning]:", message
        else:
            if perforce_settings.get('perforce_warnings_enabled'):
                print "Perforce [warning]: View does not contain a file"


# List Checked Out Files section
class ListCheckedOutFilesThread(threading.Thread):
    def __init__(self, window):
        self.window = window
        threading.Thread.__init__(self)

    def ConvertFileNameToFileOnDisk(self, in_filename):
        filename = GetClientRoot() + os.sep + in_filename.replace('\\', os.sep).replace('/', os.sep)

        return filename

    def MakeFileListFromChangelist(self, in_changelist):
        files_list = []

        # Launch p4 opened to retrieve all files from changelist
        command = 'p4 opened -c ' + in_changelist
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=None, shell=True)
        result, err = p.communicate()
        if(not err):
            lines = result.splitlines()
            for line in lines:
                file = line.split(' ')[0]
                # remove the change #
                poundindex = file.rfind('#')
                cleanedfile = file[0:poundindex]

                # just keep the filename
                cleanedfile = '/'.join(cleanedfile.split('/')[3:])

                file_entry = [cleanedfile[cleanedfile.rfind('/')+1:]]
                file_entry.append("Changelist: " + in_changelist);
                localfile = self.ConvertFileNameToFileOnDisk(cleanedfile)
                file_entry.append(localfile)
                
                files_list.append(file_entry)
        return files_list

    def MakeCheckedOutFileList(self):
        files_list = self.MakeFileListFromChangelist('default');

        # Launch p4 changes to retrieve all the pending changelists
        command = 'p4 changes -s pending'   
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=None, shell=True)
        result, err = p.communicate()

        if(not err):
            changelists = result.splitlines()

            # for each line, extract the change, and run p4 opened on it to list all the files
            for changelistline in changelists:
                changelistlinesplit = changelistline.split(' ')
                files_list.extend(self.MakeFileListFromChangelist(changelistlinesplit[1]))

        return files_list

    def run(self):
        self.files_list = self.MakeCheckedOutFileList()

        def show_quick_panel():
            if not self.files_list:
                sublime.error_message(__name__ + ': There are no checked out files ' +
                    'to list.')
                return
            self.window.show_quick_panel(self.files_list, self.on_done)
        sublime.set_timeout(show_quick_panel, 10)

    def on_done(self, picked):
        if picked == -1:
            return
        file_name = self.files_list[picked][2]

        def open_file():
            self.window.open_file(file_name)
        sublime.set_timeout(open_file, 10)


class PerforceListCheckedOutFilesCommand(sublime_plugin.WindowCommand):
    def run(self):
        ListCheckedOutFilesThread(self.window).start()