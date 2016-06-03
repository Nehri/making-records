# Record Generation
A repository that accumulates various ways to technologically generate records.

## Usage
First, you need to `pip install` a bunch of libraries.
STL generation requires `pydub`, `numpy`, `numpy-stl`, and `enum34`.
Laser cut PDF generation requires `pydub` and `reportlab`.

Next, run the program using the .mp3 or .wav file of your choice.

The command to run the STL generation is `python stl_generate.py name_of_file.extension`

The command to run the PDF generation is `python laser_cut_generator.py name_of_file.extension`

These use Python 2.7. Python 3.4 has not been tested.
