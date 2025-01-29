# ----------------------------------------------------------------------
#
# Copyright 2009-2021 Vutara and University of Utah. All rights reserved
#
# ----------------------------------------------------------------------

import os
import numpy as np
import json
import csv
import tifffile as tif
import struct

data_config = {}
frame_info = []
exp_dir_path = None

import glob

#############################################################
# Read configuration files in experiment dir
# -----------------------------------------------------------
def initExperimentDir(dir_path) :
    global exp_dir_path
    exp_dir_path = dir_path
    file_path = os.path.join(exp_dir_path, "Raw Images")
    print("file_path", file_path)
    if not os.path.isdir(file_path):
        print("Initialization failed: Could not find Raw Images directory!")
        return False
    
    data_config_path = os.path.join(file_path, "data.json")
    if not os.path.exists(data_config_path):
        print("Initialization failed: Could not find data.json file!")
        return False
    global data_config
    data_config = readDataConfig(data_config_path)

    frame_info_path = os.path.join(file_path, "frameinfo.csv")
    if not os.path.exists(frame_info_path):
        print("Initialization failed: Could not find frameinfo.csv file!")
        return False
    global frame_info
    frame_info = readFrameInfo(frame_info_path)

    return True

#############################################################
# 
# -----------------------------------------------------------
def isInitialized():
    return bool(data_config) == True and \
        len(frame_info) > 0 and \
        exp_dir_path is not None
    

#############################################################
# Read data.json as dict
# -----------------------------------------------------------
def readDataConfig(data_config_path):
    config = {}
    with open(data_config_path) as data_config_json_file:
        config = json.load(data_config_json_file)
        if config["type"] != "DataConfiguration":
            print("Invalid data.json file")
            config = {}
            
    return config["value"]

#############################################################
# Read frameinfo.csv file into list
# -----------------------------------------------------------
def readFrameInfo(frame_info_path):
    info = []
    with open(frame_info_path) as frame_info_file:
        for line in csv.DictReader(frame_info_file):
            info.append(line)
    return info

#############################################################
# Compare entries in frame info dict
# -----------------------------------------------------------
def frameCompare(frame_dict, timepoint, cycle, z, probe, frame):
    zstack_mode = data_config["Recording"]["ZStackMode"]
    if int(frame_dict["Timepoint"]) < timepoint:
        return -1
    elif int(frame_dict["Timepoint"]) > timepoint:
        return 1
    else:
        if int(frame_dict["Cycle"]) < cycle:
            return -1
        elif int(frame_dict["Cycle"]) > cycle:
            return 1
        else:
            if zstack_mode == "sequential" and int(frame_dict["Probe"]) < probe:
                return -1
            elif zstack_mode == "sequential" and int(frame_dict["Probe"]) > probe:
                return 1
            elif zstack_mode == "interleaved" and int(frame_dict["ZPos"]) < z:
                return -1
            elif zstack_mode == "interleaved" and int(frame_dict["ZPos"]) > z:
                return 1
            else:
                if zstack_mode == "sequential" and int(frame_dict["ZPos"]) < z:
                    return -1
                elif zstack_mode == "sequential" and int(frame_dict["ZPos"]) > z:
                    return 1
                elif zstack_mode == "interleaved" and int(frame_dict["Probe"]) < probe:
                    return -1
                elif zstack_mode == "interleaved" and int(frame_dict["Probe"]) > probe:
                    return 1
                else:
                    if int(frame_dict["Frame"]) < frame:
                        return -1
                    elif int(frame_dict["Frame"]) > frame:
                        return 1

    return 0


#############################################################
# Look up global index from frame info dict
# -----------------------------------------------------------
def globalIndexFromFrameInfo(timepoint, cycle, z, probe, frame):
    first = 0
    last = len(frame_info)-1
    if frameCompare(frame_info[first], timepoint, cycle, z, probe, frame) == 0:
        return int(frame_info[first]["GlobalIndex"])

    if frameCompare(frame_info[last], timepoint, cycle, z, probe, frame) == 0:
        return int(frame_info[last]["GlobalIndex"])

    next = 0
    while first != last:
        prev_next = next
        next = int((first+last)/2)
        if prev_next == next:
            exit(0)
        comp = frameCompare(frame_info[next], timepoint, cycle, z, probe, frame)
        if comp > 0:
            last = next
        elif comp < 0:
            first = next
        else:
            return int(frame_info[next]["GlobalIndex"])
    return -1

#############################################################
# Normalize image
# Returned image is numpy array of float32 with values [0,1]
# -----------------------------------------------------------
def normalizeImage(img):
    fimg = img.astype(np.float32)
    norm = np.linalg.norm(fimg)
    if norm == 0:
        return fimg
    return fimg/norm


#############################################################
# read a single image from a .dat file.
# Returned image is numpy array of uint16
# -----------------------------------------------------------
def readImage(global_idx):
    if not isInitialized():
        print("Error: Experiment directory has not been initialized!\n"
              "Try initExperimentDir() first.")
        return None
    
    dim_x = data_config["Image"]["DimX"]
    dim_y = data_config["Image"]["DimY"]
    frames_per_batch = data_config["Recording"]["FramesPerBatch"]

    # determine which file the image is in
    batch = int(global_idx / frames_per_batch)
    index = global_idx % frames_per_batch
    batch_file_name = "img" + str(batch).zfill(6) + ".dat"

    # read the image and format to proper size
    file_path = os.path.join(exp_dir_path, "Raw Images")
    img_file = os.path.join(file_path, batch_file_name)
    img_size = dim_x * dim_y
    img_data = np.fromfile(img_file, dtype='uint16')
    #print(img_data.dtype, img_data.shape)
    img_start = index*img_size
    img_end = (index+1)*img_size
    img = img_data[img_start:img_end].reshape(dim_x, dim_y)

    return img


#############################################################
# read a z stack of images from a .dat file
# -----------------------------------------------------------
def readImageStackAsUint16(timepoint, cycle, probe, frame):
    if not isInitialized():
        print("Error: Experiment directory has not been initialized!\n"
              "Try initExperimentDir() first.")
        return None
    
    dim_x = data_config["Image"]["DimX"]
    dim_y = data_config["Image"]["DimY"]
    num_z = data_config["Recording"]["NumZPos"]
    global_idxs = []
    for i in range(num_z):
        idx = globalIndexFromFrameInfo(timepoint, cycle, i, probe, frame)
        global_idxs.append(idx)
    img_stack = np.empty((len(global_idxs), dim_x, dim_y)).astype('uint16')
    for i in range(len(global_idxs)):
        img_stack[i] = readImage(global_idxs[i])

    #print(img_stack.dtype)

    return img_stack

#
def readImageStackAsUint16_edit(exp_dir, n_probe):

    dim_x = data_config["Image"]["DimX"]
    dim_y = data_config["Image"]["DimY"]
    num_z = data_config["Recording"]["NumZPos"]

    # read the image and format to proper size
    file_path = os.path.join(exp_dir, "Raw Images")
    img_file = sorted(glob.glob('%s/*img*.dat' % (file_path)))
    img = np.fromfile(img_file[0], dtype='uint16')
    if len(img_file) > 1:
        for img_fl in img_file[1:]:
            img_tmp = np.fromfile(img_fl, dtype='uint16')
            img = np.concatenate((img, img_tmp), axis=0)

    img = img.reshape((n_probe, num_z,  dim_y, dim_x))

    return img


#############################################################
# read a z stack of images from a .dat file
# -----------------------------------------------------------
def readImageStackAsFloat32(timepoint, cycle, probe, frame):
    if not isInitialized():
        print("Error: Experiment directory has not been initialized!\n"
              "Try initExperimentDir() first.")
        return None
    
    dim_x = data_config["Image"]["DimX"]
    dim_y = data_config["Image"]["DimY"]
    num_z = data_config["Recording"]["NumZPos"]
    global_idxs = []
    for i in range(num_z):
        idx = globalIndexFromFrameInfo(timepoint, cycle, i, probe, frame)
        global_idxs.append(idx)
    img_stack = np.empty((len(global_idxs), dim_x, dim_y))
    for i in range(len(global_idxs)):
        img = readImage(global_idxs[i])
        fimg = normalizeImage(img)
        img_stack[i] = fimg

    return img_stack

#############################################################
# write a numpy uint16 image stack as a TIFF
# -----------------------------------------------------------
def writeImageStackAsTiff(img_stack, output_path):
    tif.imsave(output_path, img_stack, bigtiff=True)


#############################################################
# Read a particle.dat or particle.dat.gz file and return
# the column names and data table
# -----------------------------------------------------------
def readParticleFile(file_path):
    if not os.path.exists(file_path):
        print("Error: Could not find file " + file_path)
        return [],[]

    file_name, file_ext = os.path.splitext(file_path)
    file_content = None
    
    if file_ext == ".dat":
        with open(file_path, 'rb') as f:
            file_content = f.read()
    elif file_ext == ".gz":
        with gzip.open(file_path, 'rb') as f:
            file_content = f.read()
    else:
        print("Error: Invalid file format!")
        return [],[]

    if file_content is None or len(file_content) == 0:
        print("Error: Empty file!")
        return [],[]

    # read header

    # first 4 bytes is the number of columns
    num_cols = struct.unpack("<i", file_content[:4])[0]
    print ("Found ", num_cols, " columns")
    byte_curr = 4
    
    column_names = []
    column_bytes = []
    column_types = []
    # For each column we process header info
    # 4 byte int entry for the name string length
    # variable bytes for the name string
    # 4 byte int for the number of bytes in the particle data for this column
    for c in range(num_cols):
        # get length of name string in bytes
        col_len = struct.unpack("<i", file_content[byte_curr:(byte_curr+4)])[0]
        byte_curr = byte_curr + 4

        # get name string
        col_name = struct.unpack("<"+str(col_len)+"s", file_content[byte_curr:(byte_curr+col_len)])[0]
        column_names.append(col_name)
        byte_curr = byte_curr + col_len

        # get particle data byte count
        col_bytes = struct.unpack("<i", file_content[byte_curr:(byte_curr+4)])[0]
        column_bytes.append(col_bytes)
        byte_curr = byte_curr + 4
        
        # infer type from number of bytes and name
        if col_bytes == 1: # 1 byte is always a boolean
            column_types.append("<?")
        elif col_bytes == 4: # 4 bytes is always an int
            column_types.append("<i")
        elif col_bytes == 8 and col_name == b'frame-timestamp': # 8 bytes can be a int64 if it is a timestamp
            column_types.append("<q")
        elif col_bytes == 8: # typically 8 bytes is a double
            column_types.append("<d")
        else:
            print("Error: Detected unknown byte length for column ", colName, "!")
            return [],[]

    # read particles
    print("Reading particles...")
    # collect data in one large 2D array
    point_data = [[] for i in range(num_cols)]

    # Go until we run out of lines
    while byte_curr < len(file_content):
        for c in range(num_cols):
            val = struct.unpack(column_types[c], file_content[byte_curr:(byte_curr+column_bytes[c])])[0]
            point_data[c].append(val)
            byte_curr = byte_curr + column_bytes[c]

    num_points = len(point_data[0])
    print("Read ", num_points, " points")

    return column_names, point_data


#############################################################
# Read view state. Returns a dictionary of views.
# Input is an experiment directory.
# -----------------------------------------------------------
def readViewInfo(exp_dir):
    view_data = {}
    view_path = os.path.join(exp_dir, "Views/ViewInfo.json")
    if os.path.exists(view_path):
        with open(view_path) as view_file:
            view_data = json.load(view_file)
            if view_data["type"] != "ViewState":
                print("Invalid json file")
                view_data = {}
    else:
        print("Error: ViewInfo.json not found!")

    return view_data

#############################################################
# Find full path for a view given only it's name.
# Input is an experiment directory and a view name.
# -----------------------------------------------------------
def viewNameToPath(exp_dir, view_name):
    view_data = readViewInfo(exp_dir)
    if not bool(view_data):
        return None

    for view in view_data["value"]["Views"]:
        if view["Name"] == view_name:
            view_dir = view["DirName"]
            return os.path.join(exp_dir, "Views", view_dir)

    return None
    

#############################################################
# Read saved genomics results. Returns a dictionary of settings and a
# table of loci.  Input is a View directory.
# -----------------------------------------------------------
def readGenomicsFile(view_dir):
    meta_data_file_name = os.path.join(view_dir, "GenomicsData.json")
    barcode_file_name = os.path.join(view_dir, "GenomicsBarcodes.json")
    loci_source_file_name = os.path.join(view_dir, "GenomicsDataSourceLoci.csv")
    loci_fiducial_file_name = os.path.join(view_dir, "GenomicsDataFiducialLoci.csv")

    meta_data = {}
    barcode_data = {}
    loci_source = []
    loci_fiducial = []

    if os.path.exists(meta_data_file_name):
        with open(meta_data_file_name) as meta_data_json_file:
            meta_data = json.load(meta_data_json_file)
            if meta_data["type"] != "GenomicsOrcaData":
                print("Invalid json file")
                meta_data = {}
    else:
        print("Error: GenomicsData.json not found!")
        

    if os.path.exists(barcode_file_name):
        with open(barcode_file_name) as barcode_json_file:
            barcode_data = json.load(barcode_json_file)
            if barcode_data["type"] != "GenomicsOrcaBarcodeState":
                print("Invalid json file")
                barcode_data = {}
    else:
        print("Error: GenomicsBarcodes.json not found!")

    
    if os.path.exists(loci_source_file_name):
        with open(loci_source_file_name) as loci_source_file:
            for line in csv.DictReader(loci_source_file):
                loci_source.append(line)
    else:
        print("Error: GenomicsDataSourceLoci.csv not found!")


    if os.path.exists(loci_fiducial_file_name):
        with open(loci_fiducial_file_name) as loci_fiducial_file:
            for line in csv.DictReader(loci_fiducial_file):
                loci_fiducial.append(line)
    else:    
        print("Error: GenomicsDataFiducialLoci.csv not found!")

        
    return meta_data, barcode_data, loci_source, loci_fiducial

                                         
