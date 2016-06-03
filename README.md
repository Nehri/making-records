# Record Generation v.1.0
A repository that accumulates various ways to technologically generate records.

## Usage
First, you need to `pip install` a bunch of libraries.
STL generation requires `pydub`, `numpy`, `numpy-stl`, and `enum34`.
Laser cut PDF generation requires `pydub` and `reportlab`.

Next, run the program using the .mp3 or .wav file of your choice.

The command to run the STL generation is `python stl_generator.py name_of_file.extension`

The command to run the PDF generation is `python laser_cut_generator.py name_of_file.extension`

These use Python 2.7. Python 3.4 has not been tested.

## Warnings
These files are provided for personal use only. No guarantees are made about the working nature of the scripts.

STL generation takes a very long time; it may crash your computer. 

PDF may take several minutes, depending on the computer. It outputs a group of files.

These scripts accept ONLY .mp3 and .wav input. Any other file extension will crash them.

The audio file being run must either A) be in the same directory as the python script or B) use a relative path so that the script can access it correctly.

## Credits
Python code written by Michelle Ross and Aaron Schaer.

This project builds directly off of Amanda Ghassaei's code (originally in Processing) and uses much of her coding logic.


