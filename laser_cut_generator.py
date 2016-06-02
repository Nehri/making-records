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
scale_num = 72.0
amplitude = 10.0/dpi*scale_num
min_distance = 6.0/dpi*scale_num
spacing = 10.0/dpi*scale_num
size = (cutter_width*scale_num, cutter_height*scale_num)
theta_increments = math.pi*2.0/theta_per_cycle
rad_increments = (2.0*amplitude+spacing)/theta_per_cycle
bitDepth = 8#target bitDepth
frate = 44100#target frame rate

########################################
#                                      #
#          HELPER FUNCTIONS            #
#                                      #
########################################
#Processes a text file separated by commas to return
#aa list of floats and a length, representing
#the amplitudes at every sample poiunts of the audio
def process_audio_text(filename):
	raw_data= list()
	points_data = list()
	final_points_data = list()
	max_val = 0
	with open(filename) as f:
		raw_data = f.read().splitlines()
	for x in raw_data[0].split(','):
		if x:
			points_data.append(int(x))
			if abs(int(x)) > max_val:
				max_val = abs(int(x))
	points_len = len(points_data)
	for x in range(points_len):
		points_data[x] *= amplitude/float(max_val)

	return (points_data, points_len)


#Opens the filename given in the program args,
#converts to wav if neccesary,
#then returns a list of floats representing
#the amplitudes at every sample point of the audio
def processAudioData():

  filename = sys.argv[1]
  audioData = [] #list of floats to return

  if filename[-4:] == ".mp3": #convert mp3 files

    #resaves the file as a .wav so that
    #it can be re-read as a .wav
    path = os.getcwd()
    sound = AudioSegment.from_mp3(path + "/" + filename)
    sound.export(path + "/" + filename[:-4] + ".wav", format="wav")
    filename = filename[:-4] + ".wav" #change the filename to match

  #read file and get data
  w = wave.open(filename, 'r')
  numframes = w.getnframes()

  frame = w.readframes(numframes)#w.getnframes()
  frameInt = map(ord, list(frame))#turn into array

  #separate left and right channels and merge bytes
  frameOneChannel = [0]*numframes#initialize list of one channel of wave
  for i in range(numframes):
      frameOneChannel[i] = frameInt[4*i+1]*2**8+frameInt[4*i]#separate channels and store one channel in new list
      if frameOneChannel[i] > 2**15:
          frameOneChannel[i] = (frameOneChannel[i]-2**16)
      elif frameOneChannel[i] == 2**15:
          frameOneChannel[i] = 0
      else:
          frameOneChannel[i] = frameOneChannel[i]

  #convert to list of floats
  for i in range(numframes):
      audioData.append(frameOneChannel[i])
  
  #normalize audio data to given bitdepth
  #first find max val
  maxval = 0
  for data in audioData:
    maxval = max(abs(data),maxval)

  length = len(audioData)
  #normalize amplitude to max val
  for i in range(length):
    audioData[i]*=amplitude/maxval
  
  return (audioData,length)


########################################
#                                      #
#                MAIN                  #
#                                      #
########################################
def main():
	full_filename = sys.argv[1]
	stripped_filename = full_filename[:-4] # removes the .txt extension
	
	(points_data, points_length) = processAudioData()
	radius = outer_rad*scale_num
	#storage
	section = 1
	rad_calculation = 0
	x_val = 0.0
	y_val = 0.0
	theta = float(0)
	x_val_last = 0.0
	y_val_last = 0.0
	


	c = canvas.Canvas(stripped_filename+"0.pdf")

	c.setLineWidth(0.001)
	c.setStrokeColorRGB(0,0,0)
	c.setPageSize(size)

	while theta < math.pi*2:
		rad_calculation = radius
		x_val = 6*scale_num+rad_calculation*math.cos(theta)
		y_val = 6*scale_num-rad_calculation*math.sin(theta)

		if ((x_val_last - x_val)**2 +(y_val_last-y_val)**2)>min_distance**2:
			if x_val_last != 0.0 and y_val_last != 0.0:
				c.line(x_val_last, y_val_last, x_val, y_val)
			x_val_last = x_val
			y_val_last = y_val

		radius -= rad_increments
		theta += theta_increments

	num_grooves = 1.0
	index = 0
	index_increments = int((sampling_rate*sec_per_min/rpm)/theta_per_cycle)

	while radius > inner_rad*scale_num and index < points_length-theta_per_cycle*index_increments:
		theta = 0
		while theta < math.pi*2:
			rad_calculation = radius + points_data[index]
			index += index_increments
			x_val = 6*scale_num+rad_calculation*math.cos(theta)
			y_val = 6*scale_num-rad_calculation*math.sin(theta)

			if ((x_val_last - x_val)**2 +(y_val_last-y_val)**2)>min_distance**2:
				c.line(x_val_last, y_val_last, x_val, y_val)
				x_val_last = x_val
				y_val_last = y_val

			radius -= rad_increments
			theta += theta_increments
		num_grooves+=1
		if num_grooves % num_grooves_per_file == 0:
			c.save()
			print("Finished a pdf")
			file_number = str(int(num_grooves / num_grooves_per_file))
			c = canvas.Canvas(stripped_filename+file_number+".pdf")
			c.setLineWidth(0.001)
			c.setStrokeColorRGB(0,0,0)
			c.setPageSize(size)

	theta = 0
	while theta < math.pi*2:
		#print("completing second to last circle")
		rad_calculation = radius
		x_val = 6*scale_num+rad_calculation*math.cos(theta)
		y_val = 6*scale_num-rad_calculation*math.sin(theta)

		if ((x_val_last - x_val)**2 +(y_val_last-y_val)**2)>min_distance**2:
			c.line(x_val_last, y_val_last, x_val, y_val)
			x_val_last = x_val
			y_val_last = y_val

		radius -= rad_increments
		theta += theta_increments
	theta = 0
	while theta < math.pi*2:
		#print("completing last circle")
		x_val = 6*scale_num+rad_calculation*math.cos(theta)
		y_val = 6*scale_num-rad_calculation*math.sin(theta)

		if ((x_val_last - x_val)**2 +(y_val_last-y_val)**2)>min_distance**2:
			c.line(x_val_last, y_val_last, x_val, y_val)
			x_val_last = x_val
			y_val_last = y_val

		theta += theta_increments

	if cutlines:
		c.setStrokeColorRGB(255,0,0)

		c.circle(6*scale_num,6*scale_num, hole_rad*scale_num/2, stroke=1, fill=0)
		c.circle(6*scale_num,6*scale_num, diameter*scale_num/2, stroke=1, fill=0)
	c.save()


main()
#if __name__ == '__main__':
#	main()