########################################
#                                      #
#              IMPORTS                 #
#                                      #
########################################
import math
import sys
import os
import wave
import struct
from pydub import AudioSegment
from reportlab.pdfgen import canvas

########################################
#                                      #
#              GLOBALS                 #
#                                      #
########################################
rpm = 45.0 # options are 33.3, 45, or 78
sampling_rate = 44100.0 # default sampling rate for mp3
dpi = 1200.0
cutter_width = 32 # HAL printer bed width in inches
cutter_height = 18 # HAL printer bed height in inches
theta_per_cycle = 5880.0
diameter = 11.8 # record's diameter
hole_rad = 0.286 # center hole's radius in inches
inner_rad = 2.25 # innermost groove radius in inches
outer_rad = 5.75 # outermost groove radius in inches
cutlines = True
drawBoundingBox = False
num_grooves_per_file = 5 # splits the grooves into multiple files
sec_per_min = 60
scale_num = 72.0 #amplifies the data to fit a standard 11.8" record
amplitude = 10.0/dpi*scale_num
min_distance = 6.0/dpi*scale_num
spacing = 10.0/dpi*scale_num
size = (cutter_width*scale_num, cutter_height*scale_num)
theta_increments = math.pi*2.0/theta_per_cycle
rad_increments = (2.0*amplitude+spacing)/theta_per_cycle
index_increments = int((sampling_rate*sec_per_min/rpm)/theta_per_cycle)

########################################
#                                      #
#              CLASSES                 #
#                                      #
########################################

class CircleData:
	def __init__(self, ps, rad, ind, e):
		self.points = ps
		self.radius = rad
		self.index = ind
		self.end = e

########################################
#                                      #
#            IO FUNCTIONS              #
#                                      #
########################################

# Opens the filename given in the program args,
# converts to wav if neccesary,
# then returns a list of floats representing
# the amplitudes at every sample point of the audio
def process_audio_data():

  filename = sys.argv[1]
  audioData = [] # list of floats to return

  if filename[-4:] == ".mp3": # convert mp3 files

    # resaves the file as a .wav so that
    # it can be re-read as a .wav
    path = os.getcwd()
    sound = AudioSegment.from_mp3(path + "/" + filename)
    sound.export(path + "/" + filename[:-4] + ".wav", format="wav")
    filename = filename[:-4] + ".wav" # change the filename to match

  # read file and get data
  w = wave.open(filename, 'r')
  numframes = w.getnframes()

  frame = w.readframes(numframes)# w.getnframes()
  frameInt = map(ord, list(frame))# turn into array

  # separate left and right channels and merge bytes
  frameOneChannel = [0]*numframes # initialize list of one channel of wave
  for i in range(numframes):
      frameOneChannel[i] = frameInt[4*i+1]*2**8+frameInt[4*i] # separate channels and store one channel in new list
      if frameOneChannel[i] > 2**15:
          frameOneChannel[i] = (frameOneChannel[i]-2**16)
      elif frameOneChannel[i] == 2**15:
          frameOneChannel[i] = 0
      else:
          frameOneChannel[i] = frameOneChannel[i]

  # convert to list of floats
  for i in range(numframes):
      audioData.append(frameOneChannel[i])
  
  # normalize audio data to given bitdepth
  # first find max val
  maxval = 0
  for data in audioData:
    maxval = max(abs(data),maxval)

  # normalize amplitude to max val
  for i in range(numframes):
    audioData[i]*=amplitude/maxval
  
  return (audioData,numframes)

# Creates and returns a canvas with default settings
# for laser cutting
def newCanvas(filename, num):
	c = canvas.Canvas(filename+str(num)+".pdf")
	c.setLineWidth(0.001)
	c.setStrokeColorRGB(0,0,0)
	c.setPageSize(size)

	return c

#######################################
#                                     #
#        GEOMETRY FUNCTIONS           #
#                                     #
#######################################

# takes in a radius to start at as well as the points
# to start at on the circle and draw one cycle of a
# spiral onto the canvas's pdf.
# Returns the locations of the last points drawn
# as a tuple to know where to continue the spiral
def drawOneCircle(canvas, circle_data):
	theta = float(0)
	(x_last, y_last) = circle_data.points
	radius = circle_data.radius
	index = circle_data.index
	last_cycle = circle_data.end
	rad_calculation = radius

	while theta < math.pi*2:
		if not last_cycle:
			rad_calculation = radius
		if index != -1.0:
			index += index_increments
		x_val = 6*scale_num+rad_calculation*math.cos(theta)
		y_val = 6*scale_num-rad_calculation*math.sin(theta)

		if ((x_last - x_val)**2 +(y_last-y_val)**2)>min_distance**2:
			if (x_last != 0.0 and y_last != 0.0) and (x_val != 0.0 and y_val != 0.0):
				canvas.line(x_last, y_last, x_val, y_val)
			x_last = x_val
			y_last = y_val

		if not last_cycle:
			radius -= rad_increments
		theta += theta_increments

	if index == -1.0:
		index = 0.0
	circle_data.points = (x_last, y_last)
	circle_data.radius = radius
	circle_data.index = index

	return circle_data

# Takes in a canvas and draws red cutlines for
# the outer edge of the record and the inner small
# hole. Returns the updated canvas
def drawCutlines(canvas):
	canvas.setStrokeColorRGB(255,0,0)

	canvas.circle(6*scale_num,6*scale_num, hole_rad*scale_num/2, stroke=1, fill=0)
	canvas.circle(6*scale_num,6*scale_num, diameter*scale_num/2, stroke=1, fill=0)

	return canvas

# Takes in a set of points and draws them with
# Connecting lines in a spiral on a series of
# pdf files
def drawSpiral((points_data, points_length)):
	stripped_filename = sys.argv[1][:-4]
	radius = outer_rad*scale_num
	last_points = (0.0,0.0)
	index = -1.0
	num_grooves = 0.0

	cur_data = CircleData(last_points,radius,index, False)

	c = newCanvas(stripped_filename, 0)

	while radius > inner_rad*scale_num and index < points_length-theta_per_cycle*index_increments:
		cur_data = drawOneCircle(c, cur_data)
		num_grooves += 1
		if num_grooves % num_grooves_per_file == 0:
			c.save()
			print("Finished a pdf")
			file_number = str(int(num_grooves / num_grooves_per_file))
			c = newCanvas(stripped_filename,file_number)
		last_points = cur_data.points
		radius = cur_data.radius
		index = cur_data.index

	cur_data.index = -1.0
	cur_data = drawOneCircle(c,cur_data)
	cur_data.index = -1.0
	cur_data.end = True
	cur_data = drawOneCircle(c,cur_data)

	if cutlines:
		c = drawCutlines(c)
	c.save()

########################################
#                                      #
#                MAIN                  #
#                                      #
########################################
def main():
	full_filename = sys.argv[1]
	stripped_filename = full_filename[:-4] # removes the .txt extension
	
	audio_data = process_audio_data()
	drawSpiral(audio_data)


main()
