#!/usr/bin/env python3

# 2018-12-17: Created by Alex Keszei
# 2020-05-21: Updated to include 'd' hotkey to mark images and ability to save/load selected file lists
# 2020-05-22: First attempt to modify the script to include particle position indicators from a coordinate file matching the base name of the image loaded.
# 2020-05-23: Loading and rewriting coordinates has an information loss problem after every iteration
# 2020-05-24: Version 1 complete. Erase function works, can use mouse scroller to adjust size of erase brush. Righ clicking activates eraser tool, just right click and drag to erase coordinates. Middlemouse click hides all marking/particle coordinates to clearly see the image below. Coordinates are loaded from .BOX files non-destructively, thus avoiding information loss on load/save iterations. New coordinates are interpolated to the .MRC image size (some minor error in that step, but nothing too bad as compared to picking manually).

# To Do: make the marker implementation read and print file base names (e.g. without .gif added) for easier use in bash later
#        is there a way to improve the box resize function? probably not super useful since it ought not to change after set
#        make a save to _manualpick.STAR function; will need to convert to centered coordinates with angstrom units

""" Use in a directory of .GIF files derived from .MRC files. Works with .BOX files to draw selected particle coordinates.
        Left click = Select particle (remove selected particle if already selected)
        Middle click = Hide all particle/highlights to see clean image
        Right click = Activate erase brush, hold & drag to erase on-the-fly
        Mouse scrollwheel = Increase/decrease eraser tool brush
"""

##########################
### FUNCTION DEFINITIONS
##########################

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
        master.title("Tk-based GIF viewer and .box editor")

        ## Menu bar layout
        ## initialize the top menu bar
        menubar = Menu(self.master)
        self.master.config(menu=menubar)
        ## add items to the menu bar
        dropdown_file = Menu(menubar)
        menubar.add_cascade(label="File", menu=dropdown_file)
        dropdown_file.add_command(label="Open gif image", command=self.load_file)
        dropdown_file.add_command(label="Load marked filelist", command=self.load_marked_filelist)
        # dropdown_file.add_command(label="Import .box coordinates", command=self.load_boxfile_coords)
        dropdown_file.add_command(label="Print marked imgs (Ctrl+S)", command=self.write_marked)
        dropdown_file.add_command(label="Exit", command=self.menu_exit)

        ## Widgets
        self.canvas = Canvas(master, width = 650, height = 600, background="gray", cursor="cross red red")
        # self.current_dir = Label(master, font=("Helvetica", 12), text="")
        self.input_text = Entry(master, width=30, font=("Helvetica", 16), highlightcolor="blue", borderwidth=None, relief=FLAT, foreground="black", background="light gray")
        self.browse = Button(master, text="Browse", command=self.load_file, width=10)
        self.mrc_dimensions_label = Label(master, font=("Helvetica", 12), text=".MRC dimensions (X, Y)")
        self.input_mrc_dimensions = Entry(master, width=18, font=("Helvetica", 12))
        self.input_mrc_dimensions.insert(END, "%s, %s" % (mrc_pixel_size_x, mrc_pixel_size_y))
        self.mrc_box_size_label = Label(master, font=("Helvetica, 12"), text=".MRC pixel box size")
        self.input_mrc_box_size = Entry(master, width=18, font=("Helvetica", 12))
        self.input_mrc_box_size.insert(END, "%s" % box_size)
        self.angpix_label = Label(master, font=("Helvetica", 12), text=".MRC Ang/pix")
        self.input_angpix = Entry(master, width=18, font=("Helvetica", 12))
        self.input_angpix.insert(END, "%s" % angpix)
        self.box_size_ang_label = Label(master, font=("Helvetica", 11), text="Box size:")
        self.box_size_ang = Label(master, font=("Helvetica italic", 10), text="%s Angstroms" % (box_size * angpix))

        ## Widget layout
        self.input_text.grid(row=0, column=0, sticky=NW, padx=5, pady=5)
        self.canvas.grid(row=1, column=0, rowspan=100) #rowspan=0)
        # self.current_dir.grid(row=1, column=0, sticky=W, padx=5)
        self.mrc_dimensions_label.grid(row=1, column=1, padx=5, sticky=(S, W))
        self.input_mrc_dimensions.grid(row=2, column=1, padx=5, pady=0, sticky=(N, W))
        self.mrc_box_size_label.grid(row=5, column=1, padx=5, pady=0, sticky=(S, W))
        self.input_mrc_box_size.grid(row=6, column=1, padx=5, pady=0, sticky=(N, W))
        self.angpix_label.grid(row=9, column=1, padx=5, pady=0, sticky=(S, W))
        self.input_angpix.grid(row=10, column=1, padx=5, pady=0, sticky=(N, W))
        self.box_size_ang_label.grid(row=13, column=1, padx=5, pady=0, sticky=S)
        self.box_size_ang.grid(row=14, column=1, padx=5, pady=0, sticky=N)
        self.browse.grid(row=100, column=1, sticky=(S, E))


        ## Key bindings
        self.canvas.bind('<Left>', lambda event: self.next_img('left'))
        self.canvas.bind('<Right>', lambda event: self.next_img('right'))
        self.canvas.bind('<d>', lambda event: self.mark_img())
        self.input_text.bind('<Control-KeyRelease-a>', lambda event: self.select_all(self.input_text))
        self.input_text.bind('<Return>', lambda event: self.choose_img())
        self.input_text.bind('<KP_Enter>', lambda event: self.choose_img()) # numpad 'Return' key
        self.input_mrc_dimensions.bind('<Return>', lambda event: self.new_mrc_dimensions())
        self.input_mrc_dimensions.bind('<KP_Enter>', lambda event: self.new_mrc_dimensions()) # numpad 'Return' key
        self.input_mrc_box_size.bind('<Return>', lambda event: self.new_box_size())
        self.input_angpix.bind('<KP_Enter>', lambda event: self.new_angpix()) # numpad 'Return' key
        self.input_angpix.bind('<Return>', lambda event: self.new_angpix())
        self.input_mrc_box_size.bind('<KP_Enter>', lambda event: self.new_box_size()) # numpad 'Return' key
        self.canvas.bind('<Control-KeyRelease-s>', lambda event: self.write_marked())
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<ButtonPress-2>", self.on_middle_mouse_press)
        self.canvas.bind("<ButtonRelease-2>", self.on_middle_mouse_release)

        self.canvas.bind("<ButtonPress-3>", self.on_right_mouse_press)
        self.canvas.bind("<ButtonRelease-3>", self.on_right_mouse_release)
        self.canvas.bind("<Motion>", self.delete_brush_cursor)

        self.canvas.bind("<MouseWheel>", self.MouseWheelHandler) # Windows, Mac: Binding to <MouseWheel> is being used
        self.canvas.bind("<Button-4>", self.MouseWheelHandler) # Linux: Binding to <Button-4> and <Button-5> is being used
        self.canvas.bind("<Button-5>", self.MouseWheelHandler)

        self.master.protocol("WM_DELETE_WINDOW", self.menu_exit)

        ## Run function to check for settings files and, if present load them into variables
        self.load_settings()

        ## Set focus to canvas, which has arrow key bindings
        self.canvas.focus_set()


    def update_input_widgets(self):
        global mrc_pixel_size_x, mrc_pixel_size_y, box_size, angpix
        # print(mrc_pixel_size_x, mrc_pixel_size_y, box_size, angpix)

        self.input_mrc_dimensions.delete(0,END)
        self.input_mrc_dimensions.insert(0, "%s, %s" % (mrc_pixel_size_x, mrc_pixel_size_y) )

        self.input_mrc_box_size.delete(0,END)
        self.input_mrc_box_size.insert(0, box_size)

        self.input_angpix.delete(0,END)
        self.input_angpix.insert(0, angpix)

        self.box_size_ang.config(text="%d Angstroms" % (box_size * angpix))
        return

    def menu_exit(self):
        """ On closing the app, save a settings file
        """
        global image_list, n, mrc_pixel_size_x, mrc_pixel_size_y, angpix, brush_size
        current_img = os.path.splitext(image_list[n])[0]
        ## save a settings file only if a project is actively open, as assessed by image_list being populated
        if len(image_list) > 0:
            with open('GIF_particle_boxer_settings.txt', 'w') as f :
                f.write("## Last used settings for GIF_particle_boxer.py\n")
                f.write("mrc_pixel_size_x %s\n" % mrc_pixel_size_x)
                f.write("mrc_pixel_size_y %s\n" % mrc_pixel_size_y)
                f.write("angpix %s\n" % angpix)
                f.write("brush_size %s\n" % brush_size)
                f.write("img_on_save %s\n" % current_img)
        sys.exit()

    def load_settings(self):
        """ On loadup, search the directory for input files and load them into RAM automatically
                >> marked_imgs.txt :: load these filenames into the 'marked_imgs' list variable
        """
        global box_size, image_list, n, image_coordinates, gif_pixel_size_x, gif_pixel_size_y, mrc_pixel_size_x, mrc_pixel_size_y, gif_box_size, img_on_save, img_on_save, angpix

        if os.path.exists('marked_imgs.txt'):
            ## update marked file list with file in directory
            with open('marked_imgs.txt', 'r') as f :
                for line in f:
                    if not line.strip() in marked_imgs:
                        marked_imgs.append(line.strip())

        if os.path.exists('GIF_particle_boxer_settings.txt'):
            ## update marked file list with file in directory
            with open('GIF_particle_boxer_settings.txt', 'r') as f :
                for line in f:
                    line2list = line.split()
                    if not '#' in line2list[0]: ## ignore comment lines
                        if line2list[0] == 'mrc_pixel_size_x':
                            mrc_pixel_size_x = int(line2list[1])
                        elif line2list[0] == 'mrc_pixel_size_y':
                            mrc_pixel_size_y = int(line2list[1])
                        elif line2list[0] == 'angpix':
                            angpix = float(line2list[1])
                        elif line2list[0] == 'brush_size':
                            brush_size = int(line2list[1])
                        elif line2list[0] == 'img_on_save':
                            img_on_save = line2list[1]
            # print(mrc_pixel_size_x, mrc_pixel_size_y, angpix, brush_size, img_on_save)

            # extract file information from selection
            file_name = img_on_save + '.gif'
            print("File selected: "+ file_name)

            # erase any previous image list and repopulate it with the new directory
            image_list = []
            image_list = self.images_in_dir('.')

            # find the index of the selected image in the new list
            n = image_list.index(file_name)

            ## redraw canvas items with updated global values as the given image index
            self.load_img(n)

        self.update_input_widgets()
        return

    def new_box_size(self):
        import re, copy
        global box_size, image_list, n, image_coordinates, gif_pixel_size_x, gif_pixel_size_y, mrc_pixel_size_x, gif_box_size
        user_input = self.input_mrc_box_size.get().strip()
        temp = re.findall(r'\d+', user_input)
        res = list(map(int, temp))

        if not len(res) == 1 or not isinstance(res[0], int) or not res[0] > 0:
            self.input_mrc_box_size.delete(0,END)
            self.input_mrc_box_size.insert(0, "pix boxsize")
            return
        elif not (res[0] % 2 == 0): # check if value is even
            self.input_mrc_box_size.delete(0,END)
            self.input_mrc_box_size.insert(0, "value must be even")
            return
        else:
            new_box_size = res[0]
            shrinkFactor_mrc2gif = gif_pixel_size_x / mrc_pixel_size_x
            old_image_coordinates = copy.deepcopy(image_coordinates) ## make a duplicate dictionary to work with
            image_coordinates = {} ## reset the global variable
            ## find the difference between current box_size and new box_size
            delta_box_size = new_box_size - box_size ## if new box size is larger than current box size this value will be positive; otherwise it is negative
            offset_box_value = delta_box_size / 2
            ## iterate over the old coordinates and repopulate the global image_coordinate with new values using the offsets required
            for input_gif_coord in old_image_coordinates:
                input_box_coord = old_image_coordinates[input_gif_coord] ## the .mrc space coordinate
                if input_box_coord == 'new_point':
                    #### interpolate .MRC coordinate from .GIF position
                    input_box_coord = ( int( input_gif_coord[0] / shrinkFactor_mrc2gif ) , int( mrc_pixel_size_y - input_gif_coord[1] / shrinkFactor_mrc2gif ) )
                offset_mrc_x = input_box_coord[0] - offset_box_value
                offset_mrc_y = input_box_coord[1] - offset_box_value
                gif_x, gif_y = ( int(offset_mrc_x * shrinkFactor_mrc2gif) , int(gif_pixel_size_y - offset_mrc_y * shrinkFactor_mrc2gif) ) # gif has inverted y-axis
                gif_box_size = int(new_box_size * shrinkFactor_mrc2gif)
                image_coordinates[ (gif_x, gif_y) ] = (offset_mrc_x, offset_mrc_y) # { ( gif_format) : ( box_Format) }, data are linked in this way to avoid transformation data loss

            box_size = new_box_size ## resize the global variable now that all calculations are complete
            gif_box_size = box_size * shrinkFactor_mrc2gif ## resize the global varaible for the size of the gif box drawn
            ## write out new .box file with updated parameters
            self.save_boxfile()
            ## redraw particle positions and boxsize with the new remapped data
            self.canvas.delete('particle_positions')
            self.draw_image_coordinates()
            ## revert focus to main canvas
            self.canvas.focus_set()

        try:
            self.new_angpix()
        except:
            return
        return

    def new_mrc_dimensions(self):
        """ Update the global 'mrc_pixel_size_x', 'mrc_pixel_size_y' variables from user input in the main window
        """
        import re ## for use of re.findall() function to extract numbers from strings
        global mrc_pixel_size_x, mrc_pixel_size_y, image_list, n
        user_input = self.input_mrc_dimensions.get().strip()
        temp = re.findall(r'\d+', user_input)
        res = list(map(int, temp))

        if not len(res) == 2:
            self.input_mrc_dimensions.delete(0,END)
            self.input_mrc_dimensions.insert(0, "mrc_X, mrc_Y")
            return
        else:
            mrc_pixel_size_x = res[0]
            mrc_pixel_size_y = res[1]
            ## we need to recalculate to map the box files to the new .MRC coordinate size
            if os.path.exists(os.path.splitext(image_list[n])[0] + '.box'):
                self.map_box2gif(os.path.splitext(image_list[n])[0] + '.box')
            ## redraw particle positions and boxsize with the new remapped data
            self.canvas.delete('particle_positions')
            self.draw_image_coordinates()
        ## revert focus to main canvas
        self.canvas.focus_set()

    def new_angpix(self):
        """ Update the global 'angpix' variable from user input in the main window
        """
        global angpix, box_size
        user_input = self.input_angpix.get().strip()
        try:
            res = float(user_input)
            angpix = res
            ## we need to recalculate the label for box size in angstroms
            self.box_size_ang.config(text="%s Angstroms" % (box_size * angpix))

            ## revert focus to main canvas
            self.canvas.focus_set()
            return
        except:
            self.input_angpix.delete(0,END)
            self.input_angpix.insert(0, "angpix")
            return

    def MouseWheelHandler(self, event):
        """ See: https://stackoverflow.com/questions/17355902/python-tkinter-binding-mousewheel-to-scrollbar
        """
        global brush_size, n

        def delta(event):
            if event.num == 5 or event.delta < 0:
                return -2
            return 2

        brush_size += delta(event)

        ## avoid negative brush_size values
        if brush_size <= 0:
            brush_size = 0

        ## draw new brush size
        x, y = event.x, event.y
        x_max = int(x + brush_size/2)
        x_min = int(x - brush_size/2)
        y_max = int(y + brush_size/2)
        y_min = int(y - brush_size/2)
        brush = self.canvas.create_rectangle(x_max, y_max, x_min, y_min, outline="green2", tags='brush')

    def check_if_two_ranges_intersect(self, x0, x1, y0, y1):
        """ For two well-ordered ranges (x0 < x1; y0 < 1), check if there is any intersection between them.
            See: https://stackoverflow.com/questions/3269434/whats-the-most-efficient-way-to-test-two-integer-ranges-for-overlap/25369187
        """
        if x0 <= y1 and y0 <= x1:
            return True
        else:
            return False

    def delete_brush_cursor(self, event):
        global RIGHT_MOUSE_PRESSED, brush_size, image_coordinates
        if RIGHT_MOUSE_PRESSED:

            x, y = event.x, event.y

            self.canvas.delete('brush')

            x_max = int(x + brush_size/2)
            x_min = int(x - brush_size/2)
            y_max = int(y + brush_size/2)
            y_min = int(y - brush_size/2)

            brush = self.canvas.create_rectangle(x_max, y_max, x_min, y_min, outline="green2", tags='brush')

            erase_coordinates = [] # avoid changing dictionary until after iteration complete
            ## find all coordinates that clash with the brush
            if len(image_coordinates) > 0:
                for coord in image_coordinates:
                    if self.check_if_two_ranges_intersect(coord[0], coord[0] + gif_box_size, x_min, x_max): # x0, x1, y0, y1
                        if self.check_if_two_ranges_intersect(coord[1], coord[1] - gif_box_size, y_min, y_max): # x0, x1, y0, y1
                            erase_coordinates.append(coord)
            ## erase all coordinates caught by the brush
            for coord in erase_coordinates:
                del image_coordinates[coord] # remove the coordinate that clashed
            ## redraw particle positions on image
            self.canvas.delete('particle_positions')
            self.draw_image_coordinates()
        else:
            return

    def on_right_mouse_press(self, event):
        global RIGHT_MOUSE_PRESSED, image_coordinates, brush_size, gif_box_size, n
        RIGHT_MOUSE_PRESSED = True
        x, y = event.x, event.y
        x_max = int(x + brush_size/2)
        x_min = int(x - brush_size/2)
        y_max = int(y + brush_size/2)
        y_min = int(y - brush_size/2)
        brush = self.canvas.create_rectangle(x_max, y_max, x_min, y_min, outline="green2", tags='brush')

        ## in case the user does not move the mouse after right-clicking, we want to find all clashes in range on this event as well
        erase_coordinates = [] # avoid changing dictionary until after iteration complete
        ## find all coordinates that clash with the brush
        if len(image_coordinates) > 0:
            for coord in image_coordinates:
                if self.check_if_two_ranges_intersect(coord[0], coord[0] + gif_box_size, x_min, x_max): # x0, x1, y0, y1
                    if self.check_if_two_ranges_intersect(coord[1], coord[1] - gif_box_size, y_min, y_max): # x0, x1, y0, y1
                        erase_coordinates.append(coord)
        ## erase all coordinates caught by the brush
        for coord in erase_coordinates:
            del image_coordinates[coord] # remove the coordinate that clashed
        ## redraw particle positions on image
        self.canvas.delete('particle_positions')
        self.draw_image_coordinates()
        return

    def on_right_mouse_release(self, event):
        global RIGHT_MOUSE_PRESSED
        RIGHT_MOUSE_PRESSED = False
        self.canvas.delete('brush') # remove any lingering brush marker
        ## update the .BOX file in case coordinates have changed
        self.save_boxfile()
        return

    def on_middle_mouse_press(self, event):
        self.canvas.delete('marker')
        self.canvas.delete('particle_positions')
        return

    def on_middle_mouse_release(self, event):
        global n
        self.load_img(n)
        return

    def save_boxfile(self):
        global image_list, n, image_coordinates, box_size, gif_box_size, gif_pixel_size_x, mrc_pixel_size_x, mrc_pixel_size_y

        # avoid bugging out when hitting 'next img' and no image is currently loaded
        try:
            # kill this function if there are no coordinates to print
            if len(image_coordinates) > 0:
                current_img_base_name = os.path.splitext(image_list[n])[0]

                with open(current_img_base_name + '.box', 'w') as boxfile : # NOTE: 'w' overwrites existing file; as compared to 'a' which appends only
                    for gif_coord in image_coordinates:
                        mrc_coord = image_coordinates[gif_coord]
                        ## new points added on the .GIF with no corresponding .MRC coordinate must interpolate to map the .GIF coordinate onto .MRC
                        ## NOTE: This remapping is imprecise due to uncompression error
                        if mrc_coord == 'new_point':
                            # print(gif_pixel_size_x, gif_pixel_size_y, mrc_pixel_size_x, mrc_pixel_size_y, box_size)
                            shrinkFactor_mrc2gif = gif_pixel_size_x / mrc_pixel_size_x
                            #### interpolate .MRC coordinate from .GIF position
                            mrc_x = int( gif_coord[0] / shrinkFactor_mrc2gif )
                            mrc_y = int( mrc_pixel_size_y - gif_coord[1] / shrinkFactor_mrc2gif )
                            # gif_box_size = int(box_size * shrinkFactor_mrc2gif)
                            boxfile.write("%s     %s    %s    %s\n" % (mrc_x, mrc_y, box_size, box_size) )
                        else: # if point is not new, we can just write the original corresponding mrc_coordinate back into the file
                            boxfile.write("%s     %s    %s    %s\n" % (mrc_coord[0], mrc_coord[1], box_size, box_size) )
        except:
            pass
        return

    def on_button_press(self, event):
        global image_coordinates, gif_box_size, n
        mouse_position = event.x, event.y
        # print("Mouse pressed at position: x, y =", mouse_position[0], mouse_position[1])

        ## when clicking, check the mouse position against loaded coordinates to figure out if the user is removing a point or adding a point
        if self.is_clashing(mouse_position): # this function will also remove the point if True
            pass
        else:
            x_coord = mouse_position[0] - int(gif_box_size / 2)
            y_coord = mouse_position[1] + int(gif_box_size / 2)
            image_coordinates[(x_coord, y_coord)] = 'new_point'
        ## redraw data on screen
        self.load_img(n)

    def is_clashing(self, mouse_position):
        """ mouse_position = tuple of form (x, y)
        """
        global image_coordinates, gif_box_size, n

        for (x_coord, y_coord) in image_coordinates:
            ## check x-position is in range for potential clash
            if x_coord <= mouse_position[0] <= x_coord + gif_box_size:
                ## check y-position is in range for potential clash
                if y_coord - gif_box_size <= mouse_position[1] <= y_coord:
                    ## if both x and y-positions are in range, we have a clash
                    del image_coordinates[(x_coord, y_coord)] # remove the coordinate that clashed
                    return True # for speed, do not check further coordinates (may have to click multiple times for severe overlaps)
        return False

    def mark_img(self):
        """ When called, this function updates a list of file names with the current active image. If the current
            img is already marked, it will be 'unmarked' (e.g. removed from the list)
        """
        global n, image_list, marked_imgs
        current_img = image_list[n]
        # print("Marked imgs = ", marked_imgs)
        print("Mark image = ", current_img)

        if not current_img in marked_imgs:
            marked_imgs.append(current_img)
            self.load_img(n) ## after updating the list, reload the canvas to show a red marker to the user
        else:
            marked_imgs.remove(current_img)
            self.load_img(n) ## reload the image canvas to remove any markers
        return

    def select_all(self, widget):
        """ This function is useful for binding Ctrl+A with
            selecting all text in an Entry widget
        """
        return widget.select_range(0, END)

    def load_file(self):
        """ Permits the system browser to be launched to select an image
            form a directory. Loads the directory and file into their
            respective variables and returns them
        """
        global file_dir, file_name, image_list, n, marked_imgs, particle_coordinates
        # See: https://stackoverflow.com/questions/9239514/filedialog-tkinter-and-opening-files
        fname = askopenfilename(parent=self.master, initialdir=".", title='Select file', filetypes=(("Graphics interchange format", "*.gif"),
                                           # ("Joint photographic experts group", "*.jpeg;*.jpg"),
                                           ("All files", "*.*") ))
        if fname:
            try:
                # extract file information from selection
                file_w_path = str(fname)
                file_dir, file_name = os.path.split(str(fname))
                print("File selected: "+ file_name)
                print("Active directory: "+ file_dir)

                # erase any previous image list and repopulate it with the new directory
                image_list = []
                image_list = self.images_in_dir(file_dir)

                # erase any marked image list or particle coordinates loaded into RAM
                marked_imgs = []
                particle_coordinates = []

                # find the index of the selected image in the new list
                n = image_list.index(file_name)

                ## redraw canvas items with updated global values as the given image index
                self.load_img(n)

                ## check if file has existing boxfile and load those coordinates into particle_coordinates variable
                self.load_coords()

                ## reload image with boxfile data
                self.load_img(n)

            except:
                showerror("Open Source File", "Failed to read file\n'%s'" % fname)
            return

    def reset_globals(self):
        global image_coordinates, gif_box_size
        image_coordinates = {}
        gif_box_size = 0
        return

    def next_img(self, direction):
        """ Increments the variable 'n' based on the direction given to the function.
        """
        global n, image_list, file_dir, image_coordinates

        ## save particles into boxfile, if coordinates are present
        if len(image_coordinates) > 0 :
            self.save_boxfile()

        if file_dir == '.':
            file_dir=os.getcwd()
            try:
                self.current_dir.config(text=file_dir + "/")
            except:
                pass
        if direction == 'right':
            n += 1
            # reset index to the first image when going past the last image in the list
            if n > len(image_list)-1 :
                n = 0
        if direction == 'left':
            n -= 1
            # reset index to the last image in the list when going past 0
            if n < 0:
                n = len(image_list)-1

        # update image list in case files have been added/removed
        image_list = []
        image_list = self.images_in_dir(file_dir)

        ## clear global variables for redraw
        self.reset_globals()

        ## load image with index 'n'
        self.load_img(n)
        return

    def load_img(self, index):
        """ Load image with specified index
        """
        global n, image_list, marked_imgs, gif_pixel_size_x, gif_pixel_size_y

        ## force a refresh on all canvas objects based on changing global variables
        self.canvas.delete('marker')
        self.canvas.delete('particle_positions')

        image_w_path = file_dir + "/" + image_list[n]

        # update label widget
        self.input_text.delete(0,END)
        self.input_text.insert(0,image_list[n])

        # load image onto canvas object using PhotoImage
        self.current_img = PhotoImage(file=image_w_path)
        self.display = self.canvas.create_image(0, 0, anchor=NW, image=self.current_img)
        self.canvas.display = self.display

        # resize canvas to match new image
        x,y = self.current_img.width(), self.current_img.height()
        self.canvas.config(width=x, height=y)
        gif_pixel_size_x = x
        gif_pixel_size_y = y

        # add an inset red border to the canvas depending if the file name exists in a given list
        current_img = image_list[n]
        if current_img in marked_imgs:
            marker_rect = self.canvas.create_rectangle(x-10,y-10, 10, 10, outline='red', width=10, tags='marker')

        if len(image_coordinates) == 0: ## avoid overwriting by only loading .box coordinates once after reset_globals() is run
            if os.path.exists(os.path.splitext(image_w_path)[0] + '.box'):
                self.map_box2gif(os.path.splitext(image_w_path)[0] + '.box')
                ## update box_size widget to reflect actual box size of loaded file
                self.input_mrc_box_size.delete(0,END)
                self.input_mrc_box_size.insert(END, "%s" % box_size)

        self.update_input_widgets()
        self.draw_image_coordinates()
        return

    def is_image(self, file):
        """ For a given file name, check if it has an appropriate suffix.
            Returns True if it is a file with proper suffix (e.g. .gif)
        """
        image_formats = [".gif"]
        for suffix in image_formats:
            if suffix in file:
                return True
        return False

    def images_in_dir(self, path) :
        """ Create a list object populated with the names of image files present
        """
        global image_list
        for file in os.listdir(path):
            if self.is_image(file):
                image_list.append(file)
        return image_list

    def choose_img(self):
        """ When called, finds the matching file name from the current list and
            loads its image and index
        """
        global image_list, n
        user_input = self.input_text.get().strip()
        if user_input in image_list:
            n = image_list.index(user_input)
            self.load_img(n)
        else:
            self.input_text.delete(0,END)
            self.input_text.insert(0,"File not found.")
        self.canvas.focus_set()

    def write_marked(self, file="marked_imgs.txt"):
        """ Write marked files (mark files with hotkey 'd') into a file; also write any image coordinates into an associated .BOX file
        """
        global marked_imgs
        ## if present, determine what entries might already exist in the target file (e.g. if continuing from a previous session)
        existing_entries = []
        if os.path.exists(file):
            with open(file, 'r') as f :
                for line in f:
                    existing_entries.append(line.strip())
        ## write new marked images into file, if any present
        with open(file, 'a') as f :
            for marked_img in marked_imgs:
                if not marked_img in existing_entries:
                    f.write("%s\n" % marked_img)
                    print("Entry written to %s: %s" % (file, marked_img))
                else:
                    print("Entry already present in file: %s" % marked_img)

        ## also save current image particle coordinates if they are present
        if len(image_coordinates) > 0:
            self.save_boxfile()

    def load_marked_filelist(self):
        global marked_imgs, n

        ## load selected file into variable fname
        fname = askopenfilename(parent=self.master, initialdir="./", title='Select file', filetypes=( ("File list", "*.txt"),("All files", "*.*") ))
        if fname:
            try:
                ## extract file information from selection
                logfile_path = str(fname)

                ## parse logfile into program
                with open(logfile_path, 'r') as file_obj :
                    for line in file_obj:
                        ## ignore header lines indicated by hash marks
                        if line[0] == '#':
                            continue
                        ## parse each line with space delimiter into a list using .split() function (e.g. img_name note -> ['img_name', 'note'])
                        column = line.split()
                        ## eliminate empty lines by removing length 0 lists
                        if len(column) == 0:
                            continue
                        ## in cases where multiple entries exist per line, take only the first entry
                        img_name = column[0]
                        # mic_name = os.path.splitext(column[0])[0] # os module path.splitext removes .MRC from input name

                        ## skip adding entry to marked list if already present (e.g. duplicates)
                        if img_name in marked_imgs:
                            continue
                        ## write entry into dictionary
                        marked_imgs.append(img_name)

            except:
                showerror("Open Source File", "Failed to read file\n'%s'" % fname)

            self.load_img(n) ## reload image in case it has now been marked

            return

    def map_box2gif(self, boxfile):
        """ Create a dictionary from data in a given .box file, mapping the .box coordinates to .gif coordinates of current image
        """
        global mrc_pixel_size_x, mrc_pixel_size_y, gif_box_size, image_coordinates, box_size, gif_pixel_size_x, gif_pixel_size_y

        shrinkFactor_mrc2gif = gif_pixel_size_x / mrc_pixel_size_x # this is how much smaller the .GIF is relative to the raw .MRC on which the .BOX file directly maps
                                                            # necessary for finding where to display the boxfile coordinates on the gif
        # reset the image_coordinates variable and repopulate it below
        image_coordinates = {}

        with open(boxfile, 'r') as f:
            counter = 0
            for line in f:
                counter += 1
                # read .box data in
                box_x_coord = int(float(line.split()[0]))
                box_y_coord = int(float(line.split()[1]))
                box_size = int(float(line.split()[2])) # .box file coordinates given as the bottom left corner of a box with this pixel width/height
                # convert .box data into .gif data
                gif_x, gif_y = ( int(box_x_coord * shrinkFactor_mrc2gif) , int(gif_pixel_size_y - box_y_coord * shrinkFactor_mrc2gif) ) # gif has inverted y-axis
                gif_box_size = int(box_size * shrinkFactor_mrc2gif)

                image_coordinates[ (gif_x, gif_y) ] = (box_x_coord, box_y_coord) # { ( gif_format) : ( box_Format) }, data are linked in this way to avoid transformation data loss
            # print(">> %s particles loaded" % counter )
        return

    def draw_image_coordinates(self):
        """ Read the global variable list of coordinates with gif and box files associated via a dictionary format, draw all gif coordinates present (regardless if they have associated box coordinates.
            Coordinates are drawn with the input coordinate assumed to be the bottom-left of a box with width/height equal to the global gif_box_size value
        """
        global image_coordinates, gif_box_size

        for coordinate in image_coordinates: # each key in image_coordinates is a gif-friendly coordinate
            x0 = coordinate[0]
            y0 = coordinate[1]
            x1 = x0 + gif_box_size
            y1 = y0 - gif_box_size # invert direction of box to take into account x0,y0 are at bottom left, not top left
            self.canvas.create_rectangle(x0, y0, x1, y1, outline='red', width=1, tags='particle_positions')


##########################
### RUN BLOCK
##########################
if __name__ == '__main__':
    n=0
    img_on_save = ''

    RIGHT_MOUSE_PRESSED = False # Flag to implement right-mouse activated brush icon

    # initialize global values here
    image_list = []
    file_name = ''
    file_dir = '.'

    marked_imgs = []

    image_coordinates = {} # dictionary in format, { (gif_x, gif_y) : (mrc_x, mrc_y), ... }, points given as top left, bottom left corner of box, respectively
    gif_box_size = 0 # how many pixels is the width and height of a particle box
    box_size = 0 # box size in .box file

    ## gif image dimensions are updated every time we load a new image, these globals are then used by other functins for scaling between .MRC pixel dimensions
    gif_pixel_size_x = 0
    gif_pixel_size_y = 0

    # box_size_angstroms = 100 # Angstroms # adjust this with a widget
    angpix = 1 # angstroms per pixel in MRC file from which GIF came from # adjust with widget
    mrc_pixel_size_x = 500
    mrc_pixel_size_y = 500

    brush_size = 20 # size of erase brush

    root = Tk()
    app = Gui(root)
    root.mainloop()
