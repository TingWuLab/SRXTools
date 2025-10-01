# ----------------------------------------------------------------------
#
# Copyright 2009-2020 Vutara and University of Utah. All rights reserved
#
# ----------------------------------------------------------------------

# readParticleFile.py
#
# A simple python3 script to read a binary particles.dat or gzipped
# binary particle.dat.gz file.  These files contain localized particle
# information from the Vutara SRX microscope.
#
# Usage: python3 readParticleFile.py <path to .dat or .dat.gz file>
#

import os
import sys
import gzip
import struct

if len(sys.argv) != 2:
    print("Usage: readParticleFile.py <path to particles.dat>")
    exit(0)

filePath = sys.argv[1]
print("Reading ", filePath)

filename, fileExt = os.path.splitext(filePath)

if fileExt == ".dat":
    with open(filePath, 'rb') as f:
        file_content = f.read()
elif fileExt == ".gz":
    with gzip.open(filePath, 'rb') as f:
        file_content = f.read()
else:
    print("Error: Invalid file format!")
    exit(0)

if len(file_content) == 0:
    print("Error: Empty file!")
    exit(0)


    
# read header

# first 4 bytes is the number of columns
numCols = struct.unpack("<i", file_content[:4])[0]
print ("Found ", numCols, " columns")
byteCurr = 4
    
columnNames = []
columnBytes = []
columnTypes = []

# For each column we process header info
# 4 byte int entry for the name string length
# variable bytes for the name string
# 4 byte int for the number of bytes in the particle data for this column
for c in range(numCols):
    # get length of name string in bytes
    colLen = struct.unpack("<i", file_content[byteCurr:(byteCurr+4)])[0]
    byteCurr = byteCurr + 4

    # get name string
    colName = struct.unpack("<"+str(colLen)+"s", file_content[byteCurr:(byteCurr+colLen)])[0]
    columnNames.append(colName)
    byteCurr = byteCurr + colLen

    # get particle data byte count
    colBytes = struct.unpack("<i", file_content[byteCurr:(byteCurr+4)])[0]
    columnBytes.append(colBytes)
    byteCurr = byteCurr + 4

    # infer type from number of bytes and name
    if colBytes == 1: # 1 byte is always a boolean
        columnTypes.append("<?")
    elif colBytes == 4: # 4 bytes is always an int
        columnTypes.append("<i")
    elif colBytes == 8 and colName == b'frame-timestamp': # 8 bytes can be a int64 if it is a timestamp
        columnTypes.append("<q")
    elif colBytes == 8: # typically 8 bytes is a double
        columnTypes.append("<d")
    else:
        print("Error: Detected unknown byte length for column ", colName, "!")
        exit(0)

# print header info
print("Header read")
print("column names: ", columnNames)
print("column bytes: ", columnBytes)
print("column inferred types: ", columnTypes)

# read particles
print("Reading particles...")

# collect data in one large 2D array
pointData = [[] for i in range(numCols)]

# Go until we run out of lines
while byteCurr < len(file_content):
    for c in range(numCols):
        val = struct.unpack(columnTypes[c], file_content[byteCurr:(byteCurr+columnBytes[c])])[0]
        pointData[c].append(val)
        byteCurr = byteCurr + columnBytes[c]

numPoints = len(pointData[0])
print("Read ", numPoints, " points")
print("Done")

# variables you should care about
# numCols: (int) number of columns read
# numPoints: (int) number of points read
# columnNames: (array of strings) byte strings that describe each column
# pointData: (2D array mixed type) the data for each point (numCols x numPoints)
