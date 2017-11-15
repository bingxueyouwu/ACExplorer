import binascii
import os
import sys
from ACExplorer import CONFIG
from ACExplorer.misc import log
from ACExplorer.ACUnity.decompressDatafile import decompressDatafile
from ACExplorer.misc import tempFiles
from ACExplorer.misc.dataTypes import LE2BE2, BEHEX2, LE2DEC2, float32

'''
This module works by calling format(fileTree, fileList, fileID)
This in turn calls recursiveFormat(fileTree, fileList, fileType, fIn, fOut)
which returns the file object (and in dev mode a formatted version of that file)
NOTE : The code does not read everything perfectly and may not read some files properly. The code can be taken as a basis for the formatting of the file but is far from perfect in many cases

'''

dev = 'dev' in sys.argv

def fOutWrite(fOut, val):
	if dev:
		fOut.write(val)

def hexSpaces(string):
	return ' '.join([binascii.hexlify(s).upper() for s in string])
	
def readStr(fIn, fOut, b):
	val = fIn.read(b)
	if dev:
		fOut.write(hexSpaces(val))
		fOut.write('\n')
	return LE2BE2(val)
	
def readID(fileTree, fileList, fIn, fOut):
	val = fIn.read(8)
	fileID = BEHEX2(val)
	if dev:
		fOut.write(hexSpaces(val))
		fOut.write('\t\t')
		if not tempFiles.exists(fileID):
			decompressDatafile(fileTree, fileList, fileID)
		data = tempFiles.read(fileID)
		if len(data) == 0:
			fOut.write('Unknown File ID')
		else:
			data = data[0]
			fOut.write(data["fileName"])
			fOut.write('\t\t')
			fOut.write(data["resourceType"])
		fOut.write('\n')
	return fileID

def readType(fIn, fOut):
	fileType = fIn.read(4)
	if dev:
		fOut.write(hexSpaces(fileType))
		fOut.write('\n')
	return LE2BE2(fileType)

def readInt(fIn, fOut, b):
	count = fIn.read(b)
	if dev:
		fOut.write(hexSpaces(count))
		fOut.write('\t\t')
		fOut.write(str(LE2DEC2(count)))
		fOut.write('\n')
	return LE2DEC2(count)
	
def readFloat32(fIn, fOut):
	val = fIn.read(4)
	if dev:
		fOut.write(hexSpaces(val))
		fOut.write('\t\t')
		fOut.write(str(float32(val)))
		fOut.write('\n')
	return float32(val)
	
def ReadRest(fIn, fOut):
	val = fIn.read()
	if dev:
		fOut.write(hexSpaces(val))
	return BEHEX2(val)

def format(fileTree, fileList, fileID):
	if not tempFiles.exists(fileID):
		decompressDatafile(fileTree, fileList, fileID)
	data = tempFiles.read(fileID)
	if len(data) == 0:
		raise Exception('file '+fileID+' is empty')
	data = data[0]
	log.info(__name__, 'Formatting '+fileID+':'+data["fileName"])
	fIn = open(data["dir"], 'rb')
	if dev:
		fOut = open(data["dir"]+'.format', 'w')
	else:
		fOut = None
	
	fileContainer = {}
	
	# file header
	readStr(fIn, fOut, 2)
	fileContainer['fileID'] = readID(fileTree, fileList, fIn, fOut)
	fileContainer['fileType'] = readType(fIn, fOut)
	fOutWrite(fOut, '\n')
	
	subFileContainer = recursiveFormat(fileTree, fileList, data["resourceType"], fIn, fOut)
	for key in subFileContainer:
		fileContainer[key] = subFileContainer[key]
	
	fileContainer['readRest'] = ReadRest(fIn, fOut)
		
	fIn.close()
	if dev:
		fOut.close()
		print data["dir"]+'.format'
		os.system('"'+data['dir']+'.format"')
		
	return fileContainer
	
def recursiveFormat(fileTree, fileList, fileType, fIn, fOut):
	log.info(__name__, 'Formatting Type: {}'.format(fileType))
	if dev:
		if not os.path.isdir(CONFIG['dumpFolder']+os.sep+'fileTypes'):
			os.makedirs(CONFIG['dumpFolder']+os.sep+'fileTypes')
		typeOut = open(CONFIG['dumpFolder']+os.sep+'fileTypes'+os.sep+fileType, 'a')
		filePointer = fIn.tell()
		fIn.seek(-12, 1)
		typeOut.write(hexSpaces(fIn.read()))
		typeOut.write('\n')
		typeOut.close()
		fIn.seek(filePointer)
	
	fileContainer = {}
	
	if fileType == "0984415E": #entity
		# data
		checkByte1 = readInt(fIn, fOut, 1) # checkbyte 03 to continue (other stuff to not? have seen 00 with data after)
		if checkByte1 != 3:
			print 'check byte not 3'
			return fileContainer
		fileContainer['transformationMtx'] = [[],[],[],[]]
		# 4x4 transformation matrix
		fOutWrite(fOut, '\nTransformation Matrix\n')
		for _ in range(4):
			for m in range(4):
				fileContainer['transformationMtx'][m].append(readFloat32(fIn, fOut))
		fOutWrite(fOut, '\n')
		
		# jump to mesh
		filePointer = fIn.tell()
		rawFile = fIn.read()
		bbloc = rawFile.find('\x3B\x96\x6E\x53')
		if bbloc == -1:
			return fileContainer
		fIn.seek(filePointer)
		readStr(fIn, fOut, bbloc-8)
		
		readID(fileTree, fileList, fIn, fOut)
		fileType2 = readType(fIn, fOut)
		subFileContainer = recursiveFormat(fileTree, fileList, fileType2, fIn, fOut)
		for key in subFileContainer:
			if key in fileContainer:
				fileContainer[key] += subFileContainer[key]
			else:
				fileContainer[key] = subFileContainer[key]
		
		filePointer = fIn.tell()
		rawFile = fIn.read()
		bbloc = rawFile.find('\x76\x34\xEC\x4A')
		if bbloc == -1:
			raise Exception()
		fIn.seek(filePointer)
		readStr(fIn, fOut, bbloc-8)
		
		fOutWrite(fOut, '\n')
		
		# data layer filter
		# 4 count, more data in here sometimes
		for _ in range(3):
			readID(fileTree, fileList, fIn, fOut)
			fileType2 = readType(fIn, fOut)
			recursiveFormat(fileTree, fileList, fileType2, fIn, fOut)
		
		# 03 end file?
		readStr(fIn, fOut, 1)
		fOutWrite(fOut, '\n')
		print fileContainer
		return fileContainer
		
		
		# original full code below
		
		
		# data
		readStr(fIn, fOut, 1) # checkbyte 03 to continue (other stuff to not? have seen 00 with data after)
		fileContainer['transformationMtx'] = [[],[],[],[]]
		# 4x4 transformation matrix
		fOutWrite(fOut, '\nTransformation Matrix\n')
		for _ in range(4):
			for m in range(4):
				fileContainer['transformationMtx'][m].append(readFloat32(fIn, fOut))
		fOutWrite(fOut, '\n')
		count1 = readInt(fIn, fOut, 4) # possibly a count
		if count1 > 20:
			log.warn(__name__, 'error reading entity file')
			# convert to an actual logger
			return fileContainer
		
		fileContainer['unknown'] = []
		
		subFileContainer = {}
		
		for _ in range(count1):
			fOutWrite(fOut, '\n')
			fileContainer['unknown'].append(readStr(fIn, fOut, 2)) # unknown
			readID(fileTree, fileList, fIn, fOut) # temporary id?
			fileType2 = readType(fIn, fOut)
			subFileContainer = recursiveFormat(fileTree, fileList, fileType2, fIn, fOut)
			for key in subFileContainer:
				if key in fileContainer:
					fileContainer[key] += subFileContainer[key]
				else:
					fileContainer[key] = subFileContainer[key]
			
			
		# float * 7
		
		# 110 bytes
		# 2 bytes
		# float
		
		# bouding box
		# id
		# type
		# float32 * 6
		# int32
		
		# entity descriptor
		# 19 bytes
		
		filePointer = fIn.tell()
		rawFile = fIn.read()
		bbloc = rawFile.find('\x76\x34\xEC\x4A')
		if bbloc == -1:
			raise Exception()
		fIn.seek(filePointer)
		readStr(fIn, fOut, bbloc-8)
		
		fOutWrite(fOut, '\n')
		
		# data layer filter
		# 4 count, more data in here sometimes
		for _ in range(3):
			readID(fileTree, fileList, fIn, fOut)
			fileType2 = readType(fIn, fOut)
			recursiveFormat(fileTree, fileList, fileType2, fIn, fOut)
		
		# 03 end file?
		readStr(fIn, fOut, 1)
		fOutWrite(fOut, '\n')
		return fileContainer
		
	elif fileType == "3F742D26":	# entity group
		checkByte1 = readInt(fIn, fOut, 1)
		if checkByte1 == 0:
			readID(fileTree, fileList, fIn, fOut)
			fileType2 = readType(fIn, fOut)
			recursiveFormat(fileTree, fileList, fileType2, fIn, fOut)
			readID(fileTree, fileList, fIn, fOut)
			fileType2 = readType(fIn, fOut)
			recursiveFormat(fileTree, fileList, fileType2, fIn, fOut)
		fileContainer['transformationMtx'] = [[],[],[],[]]
		for _ in range(4):
			for m in range(4):
				fileContainer['transformationMtx'][m].append(readFloat32(fIn, fOut))
		fOutWrite(fOut, '\n')
		count1 = readInt(fIn, fOut, 4)
		for _ in range(count1):
			readStr(fIn, fOut, 2)
			readID(fileTree, fileList, fIn, fOut)
			fileType2 = readType(fIn, fOut)
			recursiveFormat(fileTree, fileList, fileType2, fIn, fOut)
		
		
		readStr(fIn, fOut, 43)
		
		for _ in range(3):
			readID(fileTree, fileList, fIn, fOut)
			fileType2 = readType(fIn, fOut)
			recursiveFormat(fileTree, fileList, fileType2, fIn, fOut)
		fOutWrite(fOut, '\n')
		return fileContainer
	
	elif fileType == "E6545731": # mission root
		count1 = readInt(fIn, fOut, 4)
		for _ in range(count1):
			readStr(fIn, fOut, 2)
			readID(fileTree, fileList, fIn, fOut)
		fOutWrite(fOut, '\n')
		count2 = readInt(fIn, fOut, 4)
		for _ in range(count2):
			readStr(fIn, fOut, 2)
			readID(fileTree, fileList, fIn, fOut)
			fileType2 = readType(fIn, fOut)
			recursiveFormat(fileTree, fileList, fileType2, fIn, fOut)
		return fileContainer
	
	elif fileType == "414FF9F7": # mission context
		readStr(fIn, fOut, 1)
		count1 = readInt(fIn, fOut, 4)
		for _ in range(count1):
			readStr(fIn, fOut, 2)
			readID(fileTree, fileList, fIn, fOut)
			readType(fIn, fOut)
			readStr(fIn, fOut, 4)
			fOutWrite(fOut, '\n')
		fOutWrite(fOut, '\n')
		return fileContainer
	
	elif fileType == "1CBDE084":
		readStr(fIn, fOut, 2)
		readID(fileTree, fileList, fIn, fOut)
		fOutWrite(fOut, '\n')
		
		readID(fileTree, fileList, fIn, fOut)
		fileType2 = readType(fIn, fOut)
		recursiveFormat(fileTree, fileList, fileType2, fIn, fOut)
		
		readID(fileTree, fileList, fIn, fOut)
		fileType2 = readType(fIn, fOut)
		recursiveFormat(fileTree, fileList, fileType2, fIn, fOut)
		
		fileContainer['transformationMtx'] = [[],[],[],[]]
		for _ in range(4):
			for m in range(4):
				fileContainer['transformationMtx'][m].append(readFloat32(fIn, fOut))
		fOutWrite(fOut, '\n')
		
		count1 = readInt(fIn, fOut, 4)
		
		fileContainer['files'] = []
		
		for _ in range(count1):
			readStr(fIn, fOut, 1)
			# readID(fileTree, fileList, fIn, fOut)
			fileContainer['files'].append(readID(fileTree, fileList, fIn, fOut))
		fOutWrite(fOut, '\n')
		return fileContainer
		
	
	elif fileType == "2D675BA2":	# merged shape
		count1 = readInt(fIn, fOut, 4) # possibly a count
		if count1 != 0:
			log.warn(__name__, '"2D675BA2" count1 is not 0')
			return fileContainer
		count2 = readInt(fIn, fOut, 4)
		for _ in range(count2):
			readStr(fIn, fOut, 2)
			readID(fileTree, fileList, fIn, fOut)
		fOutWrite(fOut, '\n')
		count3 = readInt(fIn, fOut, 4)
		fOutWrite(fOut, '\n')
		for _ in range(count3):	# transformation matrix
			for a in range(16):
				readFloat32(fIn, fOut)
			fOutWrite(fOut, '\n')
			
		count4 = readInt(fIn, fOut, 4)
		fOutWrite(fOut, '\n')
		for _ in range(count4):
			readID(fileTree, fileList, fIn, fOut)
			fileType2 = readType(fIn, fOut)
			recursiveFormat(fileTree, fileList, fileType2, fIn, fOut)
		fOutWrite(fOut, '\n')
		return fileContainer
		
	elif fileType == "43EF99C2":	#Collision Filter Info 
		readStr(fIn, fOut, 15)
		fOutWrite(fOut, '\n')
		return fileContainer
	
	elif fileType == "AC2BBF68":	# datablock
		count1 = readInt(fIn, fOut, 4)
		fileContainer['dataBlock'] = []
		for _ in range(count1):
			readStr(fIn, fOut, 2)
			fileContainer['dataBlock'].append(readID(fileTree, fileList, fIn, fOut))
		fOutWrite(fOut, '\n')
		return fileContainer
	
	elif fileType == "EC658D29":	# visual
		readStr(fIn, fOut, 4)
		readID(fileTree, fileList, fIn, fOut)
		readStr(fIn, fOut, 1)
		fOutWrite(fOut, '\n')
		
		subFileContainer = {}
		ending0 = '00'
		while ending0 == '00' and type(subFileContainer) == dict:
			tempID = readID(fileTree, fileList, fIn, fOut) # temporary id?
			fileType2 = readType(fIn, fOut)
			subFileContainer = recursiveFormat(fileTree, fileList, fileType2, fIn, fOut)
			for key in subFileContainer:
				if key in fileContainer:
					fileContainer[key] += subFileContainer[key]
				else:
					fileContainer[key] = subFileContainer[key]
			ending0 = readStr(fIn, fOut, 1)
			
		while ending0 != '00':
			ending0 = readStr(fIn, fOut, 1)
		
		fOutWrite(fOut, '\n')
		
		for _ in range(7):
			readFloat32(fIn, fOut)
		
		return fileContainer
	
	elif fileType == "01437462":	# LOD selector
		readStr(fIn, fOut, 1)
		readID(fileTree, fileList, fIn, fOut)
		fOutWrite(fOut, '\n')
		return fileContainer
	
	elif fileType == "536E963B":	# mesh instance data
		fileContainer['LOD'] = []
		readStr(fIn, fOut, 1)
		fileContainer['LOD'].append({'fileID':readID(fileTree, fileList, fIn, fOut)})
		readStr(fIn, fOut, 40) #contains a compiled mesh instance 4368101B
		count1 = readInt(fIn, fOut, 4) # number of textures to follow
		fOutWrite(fOut, '\n')
		for n in range(count1):
			readStr(fIn, fOut, 1)
			readID(fileTree, fileList, fIn, fOut) # temporary id?
			fileType2 = readType(fIn, fOut)
			recursiveFormat(fileTree, fileList, fileType2, fIn, fOut)
		
		# readStr(fIn, fOut, 8) # two counts. first count for transformation matrix. second for more things?
		count2 = readInt(fIn, fOut, 4)
		if count2 > 20:
			print 'count2 is too large. Aborting'
			return fileContainer
		for _ in range(count2):
			for _ in range(4):
				for m in range(4):
					# fileContainer['transformationMtx'][m].append(readFloat32(fIn, fOut))
					readFloat32(fIn, fOut)
			fOutWrite(fOut, '\n')
		count3 = readInt(fIn, fOut, 4)
		if count3 > 20:
			raise Exception('count3 is too large. Aborting')
		for _ in range(count3):
			readID(fileTree, fileList, fIn, fOut)
			fileType2 = readType(fIn, fOut)
			recursiveFormat(fileTree, fileList, fileType2, fIn, fOut)
		fOutWrite(fOut, '\n')
		return fileContainer
		
	elif fileType == "7270FC9D":
		count1 = readInt(fIn, fOut, 4)
		for _ in range(count1):
			readStr(fIn, fOut, 1)
			readID(fileTree, fileList, fIn, fOut)
			
	elif fileType == "995BFBF5":
		readStr(fIn, fOut, 1)
		readID(fileTree, fileList, fIn, fOut)
		readStr(fIn, fOut, 1)
		readID(fileTree, fileList, fIn, fOut)
		readStr(fIn, fOut, 2)
		readID(fileTree, fileList, fIn, fOut)
		fOutWrite(fOut, '\n')
		return fileContainer
		
	elif fileType == "132FE22D":
		readStr(fIn, fOut, 3)
		readID(fileTree, fileList, fIn, fOut)
		readStr(fIn, fOut, 5)
		readID(fileTree, fileList, fIn, fOut)
		for _ in range(9):
			readFloat32(fIn, fOut)
		fOutWrite(fOut, '\n')
		return fileContainer
		
	elif fileType == "BE711F06":
		readStr(fIn, fOut, 3)
		fOutWrite(fOut, '\n')
		return fileContainer
		
	elif fileType == "2AA179AB":
		readStr(fIn, fOut, 3)
		fOutWrite(fOut, '\n')
		return fileContainer
		
	elif fileType == 'B8B08A89':
		readStr(fIn, fOut, 1)
		readID(fileTree, fileList, fIn, fOut)
		readStr(fIn, fOut, 1)
		fOutWrite(fOut, '\n')
		return fileContainer
	
	elif fileType == "2E8B5553":	# Event Listener 
		readStr(fIn, fOut, 2)
		fOutWrite(fOut, '\n')
		return fileContainer
		
	elif fileType == '4AEC3476':	# bounding volume
		for _ in range(6):
			readFloat32(fIn, fOut)
		readInt(fIn, fOut, 4)
		fOutWrite(fOut, '\n')
		return fileContainer
		
	elif fileType == '60121A9E':	# Entity Descriptor
		readStr(fIn, fOut, 19)
		fOutWrite(fOut, '\n')
		return fileContainer
		
	elif fileType == 'DB1D406E':	# Data Layer Filter 
		count1 = readInt(fIn, fOut, 4) #count
		# more data follows this if count != 0
		fOutWrite(fOut, '\n')
		return fileContainer
	
	elif fileType == '55AF1C3E':	# unknown
		readStr(fIn, fOut, 2)
		count1 = readInt(fIn, fOut, 4)
		
		if count1 > 100:
			log.warn(__name__, 'error reading unknown file type')
			# convert to an actual logger
			return fileContainer
		for _ in range(count1):
			readID(fileTree, fileList, fIn, fOut) # temporary id?
			fileType2 = readType(fIn, fOut)
			recursiveFormat(fileTree, fileList, fileType2, fIn, fOut)
		fOutWrite(fOut, '\n')
		
		count2 = readInt(fIn, fOut, 4)
		if count2 > 100:
			log.warn(__name__, 'error reading unknown file type')
			# convert to an actual logger
			return fileContainer
		for _ in range(count2):
			readStr(fIn, fOut, 12)
		fOutWrite(fOut, '\n')
			
			
		return fileContainer
		
	elif fileType == '554C614C':	# unknown
		
		fOutWrite(fOut, '\n')
		return fileContainer
		
	elif fileType == '344FA659':	# unknown
		readStr(fIn, fOut, 29)
		fOutWrite(fOut, '\n')
		return fileContainer
		
	elif fileType == '788BAA0D':	# unknown
		for _ in range(4):
			for _ in range(4):
				readFloat32(fIn, fOut)
		fOutWrite(fOut, '\n')
		return fileContainer	
		
	elif fileType == '709FB9D4':	# unknown
		readStr(fIn, fOut, 13)
		fOutWrite(fOut, '\n')
		return fileContainer
	
	else:
		fOutWrite(fOut, 'not currently supported\n')
		log.warn(__name__, fileType+' not currently supported')
		return []
		# return fileContainer