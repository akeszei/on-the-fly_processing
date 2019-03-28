# on-the-fly_processing

Designed for operation during single particle cryo-EM data collection on HMS Polara and F20 microscopes, these scripts are easily ported to work on any setup by modifying microscope specifications and programs called in 'proc_loop.sh'. 

General dependencies for these scripts are: 
  (i) bash version 4+
  (ii) python v.3
  (iii) MotionCor2 installed and in $PATH as 'MotionCor2'
  (iv) CTFFIND4 installed and in $PATH as 'ctffind' 

Together, these scripts enable easy file copying, micrograph image processing, and viewing on-the-fly:

(1) <b>copy_loop.sh </b> = Continuously copy new files using 'cp' or 'rsync' to a destination directory. Rsync supports copying over ssh protocol to remote workstations. The current implementation copies entire sub-directories and does not check for a minimum image size prior to copying. 

(2) <b>proc_loop.sh</b> = Continuously find new files of a specified name (e.g. Micrograph_name_####.tif) and process them for motion correction and CTF estimation. Results are stored in a 'on-the-fly_processing' sub-directory from the current working directory and key data are printed into terminal output and into a 'on-the-fly_data.log' file.

(3) <b>on-the-fly_logviewer.py</b> = Reads from a given 'on-the-fly_data.log' file to retrieve .GIF images of the corrected micrograph and its corresponding FFT/CTF fit for visual inspection. Once a log file is loaded images can be sequentially viewed using the <b>\<left></b> and <b>\<right></b> arrow keys or manually viewed by typing any number into the bottom right widget. The current loaded image can be marked for deletion by using the <b>\<d></b> hotkey and the list of marked images (as #### values) printed out into a 'bad_mics.txt' file with <b>\<Ctrl></b> + <b>\<s></b> or using the drop down menus. 

(4) <b>mark_listed_files.sh</b> = Read an input .txt file with a list of numbers per line (e.g. ####, of the form 'bad_mics.txt' output by on-the-fly_logviewer.py) and mark any files of a given prefix (e.g. Micrograph_name_####.tif) with a given suffix for easy downstream handling (e.g. batch deletion via: <i>rm *\<suffix></i>). 
