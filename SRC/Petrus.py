#!/usr/bin/env python

########################################################################
# Petrus.py:
# This is the Main Module of PETRUS tool
#
#  Project:        PETRUS
#  File:           Petrus.py
#  Date(YY/MM/DD): 01/02/21
#
#   Author: GNSS Academy
#   Copyright 2021 GNSS Academy
#
# -----------------------------------------------------------------
# Date       | Author             | Action
# -----------------------------------------------------------------
#
# Usage:
#   Petrus.py $SCEN_PATH
########################################################################

import sys, os

# Update Path to reach COMMON
Common = os.path.dirname(
    os.path.abspath(sys.argv[0])) + '/COMMON'
sys.path.insert(0, Common)

# Import External and Internal functions and Libraries
#----------------------------------------------------------------------
from collections import OrderedDict
from yaml import dump
from pandas import read_csv
from COMMON import GnssConstants as Const
from InputOutput import readConf
from InputOutput import processConf
from InputOutput import readRcvr
from InputOutput import createOutputFile
from InputOutput import ObsIdx
from InputOutput import readObsEpoch
from InputOutput import generatePreproFile
from InputOutput import PreproHdr
from InputOutput import CSNEPOCHS
from Preprocessing import runPreProcMeas
# from PreprocessingPlots import generatePreproPlots
from COMMON.Dates import convertJulianDay2YearMonthDay
from COMMON.Dates import convertYearMonthDay2Doy

#----------------------------------------------------------------------
# INTERNAL FUNCTIONS
#----------------------------------------------------------------------

def displayUsage():
    sys.stderr.write("ERROR: Please provide path to SCENARIO as a unique argument\n")

#######################################################
# MAIN BODY
#######################################################

# Check InputOutput Arguments
if len(sys.argv) != 2:
    displayUsage()
    sys.exit()

# Extract the arguments
Scen = sys.argv[1]

# Select the Configuratiun file name
CfgFile = Scen + '/CFG/petrus.cfg'

# Read conf file
Conf = readConf(CfgFile)
# print(dump(Conf))

# Process Configuration Parameters
Conf = processConf(Conf)

# Select the RCVR Positions file name
RcvrFile = Scen + '/INP/RCVR/' + Conf["RCVR_FILE"]

# Read RCVR Positions file
RcvrInfo = readRcvr(RcvrFile)

# Print header
print( '------------------------------------')
print( '--> RUNNING PETRUS:')
print( '------------------------------------')

# Loop over RCVRs
#-----------------------------------------------------------------------
for Rcvr in RcvrInfo.keys():
    # Display Message
    print( '\n***-----------------------------***')
    print( '*** Processing receiver: ' + Rcvr + '   ***')
    print( '***-----------------------------***')

    # Loop over Julian Days in simulation
    #-----------------------------------------------------------------------
    for Jd in range(Conf["INI_DATE_JD"], Conf["END_DATE_JD"] + 1):
        # Compute Year, Month and Day in order to build input file name
        Year, Month, Day = convertJulianDay2YearMonthDay(Jd)
        
        # Compute the Day of Year (DoY)
        Doy = convertYearMonthDay2Doy(Year, Month, Day)

        # Display Message
        print( '\n*** Processing Day of Year: ' + str(Doy) + ' ... ***')

        # Define the full path and name to the OBS INFO file to read
        ObsFile = Scen + \
            '/INP/OBS/' + "OBS_%s_Y%02dD%03d.dat" % \
                (Rcvr, Year % 100, Doy)

        # If Preprocessing outputs are activated
        if Conf["PREPRO_OUT"] == 1:
            # Define the full path and name to the output PREPRO OBS file
            PreproObsFile = Scen + \
                '/OUT/PPVE/' + "PREPRO_OBS_%s_Y%02dD%03d.dat" % \
                    (Rcvr, Year % 100, Doy)

            # Create output file
            fpreprobs = createOutputFile(PreproObsFile, PreproHdr)

        # Initialize Variables
        EndOfFile = False
        ObsInfo = [None]
        PrevPreproObsInfo = {}
        for prn in range(1, Const.MAX_NUM_SATS_CONSTEL + 1):
            PrevPreproObsInfo["G%02d" % prn] = {  #this works only for gps, mod G to not hardcoded to work with others
            "L1_n_1": 0.0,           # t-1 Carrier Phase in L1
            "L1_n_2": 0.0,           # t-2 Carrier Phase in L1
            "L1_n_3": 0.0,           # t-3 Carrier Phase in L1
            "t_n_1": 0.0,            # t-1 epoch
            "t_n_2": 0.0,            # t-2 epoch
            "t_n_3": 0.0,            # t-3 epoch
            "CsBuff": [0] * int(Conf["MIN_NCS_TH"][CSNEPOCHS]),  # Number of consecutive epochs for CS
            "CsIdx": 0,              # Index of CS detector buffer
            "ResetHatchFilter": 1,   # Flag to reset Hatch filter
            "Ksmooth": 0,            # Hatch filter K
            "PrevEpoch": 86400,      # Previous SoD
            "PrevL1": 0.0,           # Previous L1
            "PrevSmoothC1": 0.0,     # Previous Smoothed C1
            "PrevRangeRateL1": 0.0,  # Previous Code Rate
            "PrevPhaseRateL1": 0.0,  # Previous Phase Rate
            "PrevGeomFree": 0.0,     # Previous Geometry-Free Observable
            "PrevGeomFreeEpoch": 0.0,# Previous Geometry-Free Observable
            "PrevRej": 0,            # Previous Rejection flag
                                     # ...
        } # End of SatPreproObsInfo

        # Open OBS file
        ObsData=read_csv(ObsFile, delim_whitespace=True, skiprows=1, header=None,\
                         usecols=[ObsIdx["PRN"]])


        with open(ObsFile, 'r') as fobs:
            # Read header line of OBS file
            fobs.readline()

            # LOOP over all Epochs of UPOS file
            # ----------------------------------------------------------
            print("Prepocessing...")
            while not EndOfFile:

                # If ObsInfo is not empty
                if ObsInfo != []:

                    # Read Only One Epoch
                    ObsInfo = readObsEpoch(fobs)
                    # If ObsInfo is empty, exit loop
                    if ObsInfo == []:
                        break

                    # Preprocess OBS measurements
                    # ----------------------------------------------------------

                    PreproObsInfo = runPreProcMeas(Conf, RcvrInfo[Rcvr], ObsInfo, PrevPreproObsInfo,ObsData)
                    #print("out")
                    # If PREPRO outputs are requested
                    if Conf["PREPRO_OUT"] == 1:
                        # Generate output file
                        generatePreproFile(fpreprobs, PreproObsInfo)

                    # To be continued in next WP...

                # End of if ObsInfo != []:

                else:
                    EndOfFile = True

                # End of if ObsInfo != []:
                
            # End of while not EndOfFile:
    
        # End of with open(ObsFile, 'r') as f:

        # If PREPRO outputs are requested
        if Conf["PREPRO_OUT"] == 1:
            # Close PREPRO output file
            fpreprobs.close()

            # Display Message
            print("INFO: Reading file: %s and generating PREPRO figures..." %
            PreproObsFile)

            # Generate Preprocessing plots
            # generatePreproPlots(PreproObsFile)

    # End of JD loop

# End of RCVR loop

print( '\n------------------------------------')
print( '--> END OF PETRUS ANALYSIS')
print( '------------------------------------')

print( 'Check figures in output folder: PPVE/figures/')


#######################################################
# End of Petrus.py
#######################################################
