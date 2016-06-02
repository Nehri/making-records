# wav or mp3 to stl conversion - 3d printable record
# re-written by Aaron Schaer, Michelle Ross, and Steven Hernandez
# original Processing code was written by Amanda Ghassaei
# http://www.instructables.com/id/3D-Printed-Record/
# and was modified under the GNU General Public License
# to make this more flexible/portable python code

#######################################
#                                     #
#              IMPORTS                #
#                                     #
#######################################
import os
import sys
import wave
import math
import struct
import copy
from pydub import AudioSegment
import numpy
from stl import mesh

#######################################
#                                     #
#              GLOBALS                #
#                                     #
#######################################

#printer parameters
dpi = 600.0 #objet printer prints at 600 dpi
micronsPerLayer = 16.0 #microns per vertical print layer
micronsPerInch = 25400.0 

# record parameters
diameter = 11.8 #diameter of record in inches
innerHole = 0.286 #diameter of center hole in inches
innerRad = 2.35 #radius of innermost groove in inches
outerRad = 5.75 #radius of outermost groove in inches
recordHeight = 0.06 #height of top of record (inches)
recordBottom = 0.0 #height of bottom of record

#audio parameters
samplingRate = 44100.0 #(44.1khz audio initially)
rpm = 33.3 #rev per min
rateDivisor = 4.0 #how much we are downsampling by

#groove parameters
amplitude = 24.0*micronsPerLayer/micronsPerInch #amplitude of signal (in 16 micron steps)
bevel = 0.5 #bevelled groove edge
grooveWidth = 2.0/dpi #in 600dpi pixels
depth = 6.0*micronsPerLayer/micronsPerInch #measured in 16 microns steps, depth of tops of wave in groove from uppermost surface of record

#time constants
secPerMin = 60.0 #seconds per minute
thetaIter = (samplingRate*secPerMin)/(rateDivisor*rpm) #how many values of theta per cycle
incrNum = 2.0*math.pi/thetaIter #calculcate angular incrementation amount
samplenum = 0 #which audio sample we are currently on

#global vertex storage for quad stripping
recordPerimeterUpper = []
recordPerimeterLower = []
recordHoleUpper = []
recordHoleLower = []
lastEdge = []
grooveOuterUpper = []
grooveOuterLower = []
grooveInnerUpper = []
grooveInnerLower = []

#global geometry storage
vertices = [] #list of v3s
vertexCount = 0
faces = [] #list of v3s (triangles)


#######################################
#                                     #
#                MAIN                 #
#                                     #
#######################################
def main():
  
  setUpRecordShape() #draw basic shape of record
  drawGrooves(processAudioData()) #draw in grooves
  writeSTL() #output the result


#######################################
#                                     #
#            IO FUNCTIONS             #
#                                     #
#######################################

#uses numpy arrays to create a mesh from global vertices
#then outputs that mesh as an stl
def writeSTL():

  vertex_array = numpy.array(vertices)
  face_array = numpy.array(faces)

  # Create the mesh
  cube = mesh.Mesh(numpy.zeros(face_array.shape[0], dtype=mesh.Mesh.dtype))
  for i, f in enumerate(face_array):
    for j in range(3):
      cube.vectors[i][j] = vertex_array[f[j],:]

  # Write the mesh to file as an stl
  filename = sys.argv[1]
  cube.save(filename[:-4] + ".stl")


#opens the filename given in the program args
#converts to wav if neccesary
#then returns a list of floats representing
#the amplitudes at every sample point of the audio
#and the length of that list (for efficiency)
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

  #normalize amplitude to max val
  for i in range(numframes):
    audioData[i]*=amplitude/maxval
  
  return (audioData,numframes)

#######################################
#                                     #
#        GEOMETRY FUNCTIONS           #
#                                     #
#######################################

#makes the geometry for the bottom and walls of the record
#while leaving the top open so that the grooves can be drawn
def setUpRecordShape():
  
  #get vertices
  theta = 0;
  while (theta < 2*math.pi):
    #outer edge of record
    perimeterX = diameter/2+diameter/2*math.cos(theta)
    perimeterY = diameter/2+diameter/2*math.sin(theta)
    recordPerimeterUpper.append([perimeterX,perimeterY,recordHeight])
    recordPerimeterLower.append([perimeterX,perimeterY,recordBottom])
    #center hole
    centerHoleX = diameter/2+innerHole/2*math.cos(theta)
    centerHoleY = diameter/2+innerHole/2*math.sin(theta)
    recordHoleUpper.append([centerHoleX,centerHoleY,recordHeight])
    recordHoleLower.append([centerHoleX,centerHoleY,recordBottom])
    theta += incrNum
  
  #close vertex lists (closed loops)
  recordPerimeterUpper.append(recordPerimeterUpper[0])
  recordPerimeterLower.append(recordPerimeterLower[0])
  recordHoleUpper.append(recordHoleUpper[0])
  recordHoleLower.append(recordHoleLower[0])
  
  #connect vertices
  quadStrip(recordHoleUpper,recordHoleLower)
  quadStrip(recordHoleLower,recordPerimeterLower)
  quadStrip(recordPerimeterLower,recordPerimeterUpper)
  
  #to start, outer edge of record is the last egde we need to connect to with the outmost groove
  lastEdge = copy.copy(recordPerimeterUpper)
  
  print "record drawn, starting grooves"


#given two lists of vertices (3 element list of num),
#adds all the vertices to the global vertex storage
#and adds the faces for the quad strip between them to global storage
def quadStrip(vl1,vl2):

  global vertexCount
  nextIndex = vertexCount #the next index in the global struct

  #starting pair of vertices
  if (len(vl1)) > 0 and (len(vl2)) > 0:
    vertices.append(vl1[0]) #at nextIndex
    vertices.append(vl2[0]) #at nextIndex + 1
    vertexCount += 2

  for i in range(1,min(len(vl1),len(vl2))): #use the min to prevent index errors
    vertices.append(vl1[i]) #first of new pair
    vertices.append(vl2[i]) #second of new pair
    vertexCount += 2
    relativeIndex = nextIndex+(2*(i-1)) #index of the first of the previous pair
    faces.append([relativeIndex,relativeIndex+1,relativeIndex+2]) #first triangle
    faces.append([relativeIndex+1,relativeIndex+2,relativeIndex+3]) #second triangle

#fills in the top of the record geometry
#by generating all the grooves and filling the space between them
def drawGrooves(audioTuple):
  
  audioData = audioTuple[0]
  audioLen = audioTuple[1]

  grooveNum = 0 #which groove we are currently drawing
  
  #DRAW GROOVES
  radius = outerRad #outermost radius (at 5.75") to start
  radIncr = (grooveWidth+2*bevel*amplitude)/thetaIter #calculate radial incrementation amount
  totalgroovenum = int(audioLen/(rateDivisor*thetaIter))
  
  #first draw starting cap
  stop1 = beginStartCap(radius, audioData[0])
  
  #then spiral groove
  while (rateDivisor*samplenum<(audioLen-rateDivisor*thetaIter+1)): #while we still have audio to write and we have not reached the innermost groove   #radius>innerRad &&
    
    clearGrooveStorage()

    theta=0
    while (theta<2*math.pi): #for theta between 0 and 2pi
      radius = iterate(theta, radius, grooveNum, audioData, audioLen, radIncr)
      theta+=incrNum

    completeGrooveRev(grooveNum, radius, audioData, audioLen)
    connectVertices(grooveNum)

    if (grooveNum==0): #complete beginning cap if neccesary
      finishStartCap(radius, stop1)

    #tell me how much longer
    grooveNum+=1
    print str(grooveNum)+" of "+str(totalgroovenum)+" grooves drawn"


  #the locked groove is made out of two intersecting grooves, one that spirals in, and one that creates a perfect circle.
  #the ridge between these grooves gets lower and lower until it disappears and the two grooves become one wide groove.
  radius = drawPenultGroove(radius, grooveNum, audioData, audioLen, radIncr) #second to last groove
  clearGrooveStorage()

  theta=0
  while (theta<2*math.pi): #draw last groove (circular locked groove)
    iterate(theta, radius, grooveNum, [], 0, radIncr)
    theta+=incrNum

  completeGrooveRev(grooveNum, radius, [], 0)
  connectVertices(grooveNum)

  quadStrip(lastEdge,recordHoleUpper) #close remaining space between last groove and center hole

#given the float list of audio samples,
#returns the next sample, or 0 if there is none
def getNextSampleElseZero(audioData,audioLen):
  global samplenum
  aud = 0
  if (rateDivisor*samplenum>(audioLen-1)):
    aud = 0
  else:
    aud = audioData[int(rateDivisor*samplenum)]
  samplenum+=1 #increment sample num
  return aud

#given the current theta and radius (floats),
#the current groove num (int)
#the float list of audioData,
#appends vertecies calculated from from the next audio sample, 
#then returns the next radius (float),
def iterate(theta, radius, grooveNum, audioData, audioLen, radIncr):
  sineTheta = math.sin(theta)
  cosineTheta = math.cos(theta)

  #calculate height of groove
  grooveHeight = recordHeight-depth-amplitude
  if (audioLen>0): 
    grooveHeight += getNextSampleElseZero(audioData,audioLen)
  
  if (grooveNum==0):
    grooveOuterUpper.append([(diameter/2+(radius+amplitude*bevel)*cosineTheta),(diameter/2+(radius+amplitude*bevel)*sineTheta),recordHeight])

  grooveOuterLower.append([(diameter/2+radius*cosineTheta),(diameter/2+radius*sineTheta),grooveHeight])
  grooveInnerLower.append([(diameter/2+(radius-grooveWidth)*cosineTheta),(diameter/2+(radius-grooveWidth)*sineTheta),grooveHeight])
  grooveInnerUpper.append([(diameter/2+(radius-grooveWidth-amplitude*bevel)*cosineTheta),(diameter/2+(radius-grooveWidth-amplitude*bevel)*sineTheta),recordHeight])
  
  return radius - radIncr 

#given the current groove num (int), the current radius (flat),
#and the float list of audioData,
#finishes a revolution by appending vertices to the global storage
def completeGrooveRev(grooveNum, radius, audioData, audioLen):
   #add last value to grooves to complete one full rev (theta=0)
  grooveHeight = recordHeight-depth-amplitude
  if (audioLen>0):
    grooveHeight += audioData[int(rateDivisor*samplenum)]
  if (grooveNum==0): #if joining a groove to the edge of the record
    grooveOuterUpper.append(grooveInnerUpper[0])

  grooveOuterLower.append([diameter/2+radius,diameter/2,grooveHeight])
  grooveInnerLower.append([diameter/2+(radius-grooveWidth),diameter/2,grooveHeight])
  grooveInnerUpper.append([diameter/2+radius-grooveWidth-amplitude*bevel,diameter/2,recordHeight])

#given the current groove num (int)
#quad-strips the grooves to connect the vertices 
def connectVertices(grooveNum):

  global lastEdge

  #connect vertices
  if (grooveNum==0): #if joining a groove to the edge of the record
    quadStrip(lastEdge,grooveOuterUpper)
    quadStrip(grooveOuterUpper,grooveOuterLower)

  else: #if joining a groove to another groove
    quadStrip(lastEdge,grooveOuterLower)

  quadStrip(grooveOuterLower,grooveInnerLower)
  quadStrip(grooveInnerLower,grooveInnerUpper)
  
  #set new last edge
  lastEdge = copy.copy(grooveInnerUpper)

#given the current radius (float), and an audio sample (float),
#creates two stops (vector lists), quad-strips them,
#then returns the first stop
def beginStartCap(radius, firstSample): #this is a tiny piece of geometry that closes off the front end of the groove
  stop1 = []
  stop2 = []
  grooveHeight = recordHeight-depth-amplitude+firstSample
  stop1.append([(diameter/2+(radius+amplitude*bevel)),(diameter/2),recordHeight]) #outerupper
  stop2.append([diameter/2+radius,diameter/2,grooveHeight]) #outerlower
  stop2.append([diameter/2+(radius-grooveWidth),diameter/2,grooveHeight]) #innerlower
  stop1.append([(diameter/2+(radius-grooveWidth-amplitude*bevel)),diameter/2,recordHeight]) #innerupper
  quadStrip(stop1,stop2) #draw triangles
  return stop1

#given the current radius (float), and a vertex list for the previous stop
#finishes the start cap by quad-stripping the given stop with outer perimeter
def finishStartCap(radius, stop1):
  stop2 = []
  stop2.append([diameter,diameter/2,recordHeight]) #outer perimeter[0]
  stop2.append([(diameter/2+radius+amplitude*bevel),(diameter/2),recordHeight]) #outer groove edge [2pi]
  #draw triangles
  quadStrip(stop1,stop2)

#resets global groove vertex storage
def clearGrooveStorage():
  grooveOuterUpper = []
  grooveOuterLower = []
  grooveInnerUpper = []
  grooveInnerLower = []

#given the current radius (float), the current grooveNum (int)
#audio data (float list) and the radIncr rate (float)
#returns the next radius (float) after drawing the Penultimate groove 
def drawPenultGroove(radius,grooveNum,audioData,audioLen,radIncr):
  global lastEdge
  
  #the locked groove is made out of two intersecting grooves, one that spirals in, and one that creates a perfect circle.
  #the ridge between these grooves gets lower and lower until it disappears and the two grooves become on wide groove.
  changeTheta = 2*math.pi*(0.5*amplitude)/(amplitude+grooveWidth) #what value of theta to merge two last grooves
  ridgeDecrNum = 2*math.pi*amplitude/(changeTheta*thetaIter) #how fast the ridge height is decreasing
  ridgeHeight = recordHeight #center ridge starts at same height as record
  clearGrooveStorage()
  
  ridge = []
  theta = 0
  while (theta<2*math.pi): #draw part of spiral groove, until theta = changeTheta
    if (theta<=changeTheta):
      sineTheta = math.sin(theta)
      cosineTheta = math.cos(theta)
      ridge.append([(diameter/2+(radius-grooveWidth-amplitude*bevel)*cosineTheta),
        (diameter/2+(radius-grooveWidth-amplitude*bevel)*sineTheta),ridgeHeight])
      radius = iterate(theta, radius, grooveNum, audioData, audioLen, radIncr)
      ridgeHeight -= ridgeDecrNum
    else:
      break #get out of this for loop is theat > changeTheta
      
    theta+=incrNum
  
  #complete rev w/o audio data 
  grooveHeight = recordHeight-depth-amplitude #zero point for the groove
  
  sineTheta = math.sin(theta) #using theta from where we left off
  cosineTheta = math.cos(theta)
  grooveOuterLower.append([(diameter/2+radius*cosineTheta),(diameter/2+radius*sineTheta),grooveHeight])
  grooveInnerLower.append([(diameter/2+(radius-grooveWidth)*cosineTheta),
    (diameter/2+(radius-grooveWidth)*sineTheta),grooveHeight])
  ridge.append([(diameter/2+(radius-grooveWidth-amplitude*bevel)*cosineTheta),
    (diameter/2+(radius-grooveWidth-amplitude*bevel)*sineTheta),grooveHeight])
  quadStrip(grooveOuterLower,grooveInnerLower)
  quadStrip(grooveInnerLower,ridge)
  
  while(theta<2*math.pi): #for theta between current position and 2pi
    sineTheta = math.sin(theta)
    cosineTheta = math.cos(theta)
    grooveOuterLower.append([(diameter/2+radius*cosineTheta),(diameter/2+radius*sineTheta),grooveHeight])    
    ridge.append([(diameter/2+radius*cosineTheta),(diameter/2+radius*sineTheta),grooveHeight])    
    radius -= radIncr

    theta+=incrNum

  #connect vertices
  quadStrip(lastEdge,grooveOuterLower)
  
  #set new last edge
  lastEdge = copy.copy(ridge)
  
  return radius


if __name__ == "__main__":
    main()