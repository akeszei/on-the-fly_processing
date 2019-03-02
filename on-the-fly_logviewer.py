#!/usr/bin/env python3

# 2019-03-02 A.Keszei: Updated program
# add a listbox widget on the right side with a scroll bar to show marked files populating?

"""
    This script supplements my on-the-fly processing scripts to provide an easy all-in-one viewer to assess data quality and
    allows an easy, interactive way to mark files (hotkey 'd') to create a list of micrographs to throw away after data collection
    (or concievably during data collection itself). Reads data from 'on-the-fly_data.log' file produced by my 'proc_loop.sh' script
"""

##########################
### SETUP BLOCK
##########################

VERBOSE = False

from tkinter import *
from tkinter.filedialog import askopenfilename
from tkinter.messagebox import showerror
import os

class Gui:
    def __init__(self, master):
        """ The initialization scheme provides the grid layout, global keybindings,
            and widgets that constitute the main GUI window
        """
        self.master = master
        master.title("Tk-based on-the-fly EM processing logviewer")

        ## Menu bar layout
        # initialize the top menu bar
        menubar = Menu(self.master)
        self.master.config(menu=menubar)
        # add items to the menu bar
        dropdown_file = Menu(menubar)
        menubar.add_cascade(label="File", menu=dropdown_file)
        dropdown_file.add_command(label="Open log file", command=self.load_logfile)
        dropdown_file.add_command(label="Print marked imgs (Ctrl+S)", command=self.write_marked)
        dropdown_file.add_command(label="Exit", command=self.menu_exit)

        ## Widgets
        # the main canvas with the motion corrected image
        self.img_canvas = Canvas(master, width = 750, height = 750, background="gray", highlightthickness=0)
        self.display_img = self.img_canvas.create_image(0, 0, anchor=NW, image="")
        # the neighboring canvas with the CTF-fit image
        self.CTF_canvas = Canvas(master, width = 512, height = 512, background="gray")
        self.display_CTF = self.CTF_canvas.create_image(0, 0, anchor=NW, image="")

        self.img_current_dir = Label(master, font=("Helvetica", 10), text="Directory with motion corrected .GIF files...", anchor=W)
        self.CTF_current_dir = Label(master, font=("Helvetica", 10), text="Directory with CTF fit .GIF files...", anchor=W)

        self.img_name = Label(master, font=("Helvetica", 16), text="Image name")
        self.img_mark = Label(master, font=("Helvetica", 12), text="")
        self.img_dZ = Label(master, font=("Helvetica", 12), text="Est. dZ = ")
        self.img_fitRes = Label(master, font=("Helvetica", 12), text="Fit Res = ")
        self.go_to_n = Entry(master, width=30, font=("Helvetica", 14), highlightcolor="blue", borderwidth=2, relief=RIDGE, foreground="gray")
        self.go_to_n.insert(0, "Go to micrograph # ...")

        ## Widget layout
        self.img_current_dir.grid(row=0, column=0, sticky=W, padx=5, columnspan=2)
        self.CTF_current_dir.grid(row=1, column=0, sticky=W, padx=5, columnspan=2)
        self.img_canvas.grid(row=2, column=0, columnspan=1, rowspan=6, sticky=N)
        self.CTF_canvas.grid(row=2, column=1, columnspan=1, sticky=N)
        self.img_name.grid(row=3, column=1, sticky=N)
        self.img_mark.grid(row=4, column=1)
        self.img_dZ.grid(row=5, column=1)
        self.img_fitRes.grid(row=6, column=1, sticky=N)
        self.go_to_n.grid(row=7, column=1, sticky=S, pady=10)

        ## Key bindings
        self.img_canvas.bind('<Left>', lambda event: self.next_img('left'))
        self.img_canvas.bind('<Right>', lambda event: self.next_img('right'))
        self.img_canvas.bind('<d>', lambda event: self.mark_img())
        self.img_canvas.bind('<D>', lambda event: self.mark_img())
        self.img_canvas.bind('<Control-KeyRelease-s>', lambda event: self.write_marked())

        self.go_to_n.bind('<Control-KeyRelease-a>', lambda event: self.select_all(self.go_to_n))
        self.go_to_n.bind('<Return>', lambda event: self.update_num())
        self.go_to_n.bind('<KP_Enter>', lambda event: self.update_num()) # numpad 'Return' key
        self.go_to_n.bind('<Button-1>', lambda event: self.clear_entry(self.go_to_n))



        ## Set focus to canvas, which has arrow key bindings
        self.img_canvas.focus_set()

    def mark_img(self):
        """ When called, this function updates a list of file names with the current active image. If the current
            img is already marked, it will be 'unmarked' (e.g. removed from the list)
        """
        global img_prefix, n, marked_imgs
        current_img = img_prefix + ("%04d" % n)
        if not current_img in marked_imgs:
            marked_imgs.append(current_img)
            self.img_mark.config(text="MARKED FOR DELETION")
        else:
            marked_imgs.remove(current_img)
            self.img_mark.config(text="")
        if VERBOSE:
            print("Marked image list modified:")
            print(">> ", marked_imgs)


    def write_marked(self, file="bad_mics.txt"):
        """ When called, this function prints each marked file into a text document. If the file name is already
            present in a previously existing file, a duplicate is NOT printed (e.g. does not overwrite existing list, if present)
        """
        global marked_imgs
        ## if present, determine what entries might already exist in the target file (e.g. if continuing from a previous session)
        existing_entries = []
        if os.path.exists(file):
            with open(file, 'r') as f :
                for line in f:
                    existing_entries.append(line.strip())
            if VERBOSE:
                print("Existing entries present:")
                print(">> ", existing_entries)
        ## write new marked images into file, if any present
        with open(file, 'a') as f :
            for marked_img in marked_imgs:
                marked_img_number = marked_img.split('_')[-1]
                if not marked_img_number in existing_entries:
                    f.write("%s\n" % marked_img_number)
                    if True: # replaced VERBOSE with True
                        print("Entry written to %s: %s" % (file, marked_img_number))
                else:
                    pass
                    if True: # replaced VERBOSE with True
                        print("Entry already present in file: %s" % marked_img_number)

    def update_widgets(self):
        """ Read current global variables in and load the relevant images/data in to each
            widget in the GUI
        """
        global log_data, img_dir, CTF_dir, img_prefix, n, marked_imgs, logfile_path
        self.img_current_dir.config(text="IMG dir: " + os.path.split(logfile_path)[0] + '/' + img_dir)
        self.CTF_current_dir.config(text="CTF dir: " + os.path.split(logfile_path)[0] + '/' + CTF_dir)
        ## update the name by adding leading zeroes to n and merging with image prefix
        new_name = img_prefix + ("%04d" % n)
        self.img_name.config(text=new_name)
        ## check if file is marked or not, update the label widget accordingly
        if new_name in marked_imgs:
            self.img_mark.config(text="MARKED FOR DELETION")
        else:
            self.img_mark.config(text="")
        ## if the name of the image exists in the log file, load its information into the label widgets
        if new_name in log_data:
            ## update label widgets from log file
            self.img_dZ.config(text="Est. dZ = " + '-' + log_data[new_name][1])
            self.img_fitRes.config(text="Fit Res = " + log_data[new_name][0] + " A")
        else:
            self.img_dZ.config(text="Est. dZ = ")
            self.img_fitRes.config(text="Fit Res = ")
        ## if the image corresponding to the CTF of the current img exists, load it on to the CTF_canvas
        if os.path.exists(os.path.split(logfile_path)[0] + '/' + CTF_dir + '/' + new_name + '_CTF.gif'):
            ## load image onto canvas
            self.current_CTF_img = PhotoImage(file=os.path.split(logfile_path)[0] + '/' + CTF_dir + '/' + new_name + '_CTF.gif')
            self.display_CTF = self.CTF_canvas.create_image(0, 0, anchor=NW, image=self.current_CTF_img)
            self.CTF_canvas.display_CTF = self.display_CTF
            ## resize canvas to match new image
            x,y = self.current_CTF_img.width(), self.current_CTF_img.height()
            self.CTF_canvas.config(width=x, height=y)
            if VERBOSE:
                print("Loading CTF img:")
                print(">> " + new_name + '_CTF.gif' + " loaded")
        else:
            ## if it does not exist, clear the canvas
            self.CTF_canvas.itemconfig(self.display_CTF, image="", anchor=NW)
            if VERBOSE:
                print("Loading CTF img:")
                print(">> " + new_name + '_CTF.gif' + " not found!")
        ## load motion corrected image if it exists, otherwise clear the canvas
        if os.path.exists(os.path.split(logfile_path)[0] + '/' + img_dir + '/' + new_name + '.gif'):
            ## load image onto canvas
            self.current_img = PhotoImage(file=os.path.split(logfile_path)[0] + '/' + img_dir + '/' + new_name + '.gif')
            self.display_img = self.img_canvas.create_image(0, 0, anchor=NW, image=self.current_img)
            self.img_canvas.display_img = self.display_img
            ## resize canvas to match new image
            x,y = self.current_img.width(), self.current_img.height()
            self.img_canvas.config(width=x, height=y)
            if VERBOSE:
                print("Loading main img:")
                print(">> " + new_name + '.gif' + " loaded")
        else:
            ## if it does not exist, clear the canvas
            self.img_canvas.itemconfig(self.display_img, image="", anchor=NW)
            if VERBOSE:
                print("Loading main img:")
                print(">> " + new_name + '.gif' + " not found!")

    def update_num(self):
        """ Read from an Entry widget and update the global n variable before updating
            the log_data and widgets
        """
        global n, img_prefix, logfile_path
        input_value = self.go_to_n.get()
        print("INPUT value = " + input_value)
        ## confirm an integer was typed in, otherwise do not update 'n'
        try:
            n = int(input_value)
        except:
            self.go_to_n.delete(0,END)
            self.go_to_n.insert(0,"Integer value expected...")
            return
        # update log file in case new entries have been written
        self.parse_logfile(logfile_path)
        self.update_widgets()
        ## reset widget text to default after action is complete
        self.go_to_n.delete(0,END)
        self.go_to_n.insert(0,"Go to micrograph #...")
        if VERBOSE:
            print("User entry given:")
            print(">> Go to " + img_prefix + ("%04d" % n))
        self.img_canvas.focus_set() # return focus to canvas with hotkeys active

    def next_img(self, direction):
        """ Increments the variable 'n' based on the direction given to the function.
        """
        global n, logfile_path, log_data
        # update log file in case new entries have been written
        self.parse_logfile(logfile_path)

        if direction == 'right':
            n += 1
            ## reset index to the first image when going past the last image in the list
            # if n > len(log_data)-1 :
                # n = 0
        if direction == 'left':
            n -= 1
            # prevent 0 or negative image numbers
            if n < 1:
                n = 1
        self.update_widgets()
        if VERBOSE:
            print("Index value updated:")
            print(">> ", n)

    def load_logfile(self):
        global logfile_path, n
        ## reset the log_data and incrementor variables to accept new input data
        log_data = {}
        n = 1
        ## load selected file into variable fname
        fname = askopenfilename(parent=self.master, initialdir="./", title='Select file', filetypes=( ("Log file", "*.log"),("All files", "*.*") ))
        if fname:
            try:
                ## extract file information from selection
                logfile_path = str(fname)
                file_dir, file_name = os.path.split(str(fname))
                if VERBOSE:
                    print("File opened:")
                    print('>> ' + file_dir + '/' + file_name)
                ## load logfile into data
                self.parse_logfile(logfile_path)
                self.update_widgets()
            except:
                showerror("Open Source File", "Failed to read file\n'%s'" % fname)
            return

    def parse_logfile(self, file):
        """ Read logfile and extract relevant data into a dictionary format:
                log_data = {'Name_####': (CTF fit, Avg dZ, ...), ... }
            NOTE: Any extension present in the name is removed in the dictionary key name
        """
        global log_data, img_dir, CTF_dir, img_prefix, n
        with open(file, 'r') as file_obj :
            for line in file_obj:
                ## read header lines indicated by hash marks
                if line[0] == '#':
                    if 'Motion_corrected_images' in line:
                        img_dir = line.split()[2]
                        continue
                    if 'CTF_fit_images' in line:
                        CTF_dir = line.split()[2]
                        continue
                    continue
                ## parse each line with space delimiter into a list using .split() function (e.g. ['col1', 'col2', ...])
                column = line.split()
                ## eliminate empty lines by removing length 0 lists
                if len(column) == 0:
                    continue
                ## extract data into name and data parts
                mic_name = os.path.splitext(column[0])[0] # os module path.splitext removes .EXT from input name
                mic_data = tuple(column[1:]) # col1 = CTF fit (Ang); col2 = Est. avg dZ (um); ...
                ## skip adding entry to dictionary if already defined (e.g. duplicates)
                if mic_name in log_data:
                    continue
                ## write entry into dictionary
                log_data[mic_name] = mic_data
        ## use the first entry in log_data to determine the fixed image prefix used for the dataset (of the form: Name_other_..._####.EXT)
        img_prefix = '_'.join(sorted(log_data.items())[0][0].split('_')[0:-1])+'_'
        if VERBOSE:
            print("Log file loaded:")
            print('>>', 'index (n) =', n ,'\n>>', 'prefix =', img_prefix,'\n>>', 'img dir =', img_dir, '\n>>','CTF dir =', CTF_dir, '\n>>','# log file items = ', len(log_data))

    def menu_exit(self):
        """ Quit Tk program when clicking the 'Exit' button in the 'File' dropdown menu
        """
        sys.exit()

    def select_all(self, widget):
        """ This function is useful for binding Ctrl+A with selecting all text in an Entry widget
        """
        return widget.select_range(0, END)

    def clear_entry(self, widget):
        return widget.delete(0, END)







##########################
### RUN BLOCK
##########################
if __name__ == '__main__':
    root = Tk()
    app = Gui(root)

    # initialize global values here
    logfile_path = '.'
    log_data = {}
    img_dir = 'on-the-fly_processing/'
    CTF_dir = 'on-the-fly_processing/CTF/'
    img_prefix = 'stack_'

    n=0

    file_name = ''
    file_dir = '.'

    marked_imgs = []

    root.mainloop()
