#darc, the Durham Adaptive optics Real-time Controller.
#Copyright (C) 2010 Alastair Basden.

#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU Affero General Public License as
#published by the Free Software Foundation, either version 3 of the
#License, or (at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU Affero General Public License for more details.

#You should have received a copy of the GNU Affero General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.
#This is a configuration file for CANARY.
#Aim to fill up the control dictionary with values to be used in the RTCS.

#import correlation
import FITS
import tel
import numpy
#Here we are assuming scimeasure on port 0, andor on port 1.
NCAMERAS=2#1, 2, 3, 4.  This is the number of physical cameras

nacts=54#97#54#+256
ncam=2#(int(NCAMERAS)+1)/2
camPerGrab=numpy.ones((ncam,),"i")*1
if NCAMERAS%2==1:
    camPerGrab[-1]=1
ncamThreads=numpy.ones((ncam,),numpy.int32)*1
npxly=numpy.zeros((ncam,),numpy.int32)
npxly[:]=128
npxlx=npxly.copy()*camPerGrab
nsuby=npxlx.copy()
nsuby[:]=7#for config purposes only... not sent to rtc
nsubx=nsuby.copy()*camPerGrab#for config purposes - not sent to rtc
nsub=nsubx*nsuby#This is used by rtc.
nsubaps=nsub.sum()#(nsuby*nsubx).sum()
individualSubapFlag=tel.Pupil(7,3.5,1,7).subflag.astype("i")
subapFlag=numpy.zeros((nsubaps,),"i")
for i in range(ncam):
    tmp=subapFlag[nsub[:i].sum():nsub[:i+1].sum()]
    tmp.shape=nsuby[i],nsubx[i]
    for j in range(camPerGrab[i]):
        tmp[:,j::camPerGrab[i]]=individualSubapFlag
#ncents=nsubaps*2
ncents=subapFlag.sum()*2
npxls=(npxly*npxlx).sum()

fakeCCDImage=None#(numpy.random.random((npxls,))*20).astype("i")
#camimg=(numpy.random.random((10,npxls))*20).astype(numpy.int16)

bgImage=None#FITS.Read("shimgb1stripped_bg.fits")[1].astype("f")#numpy.zeros((npxls,),"f")
darkNoise=None#FITS.Read("shimgb1stripped_dm.fits")[1].astype("f")
flatField=None#FITS.Read("shimgb1stripped_ff.fits")[1].astype("f")
#indx=0
#nx=npxlx/nsubx
#ny=npxly/nsuby
#correlationPSF=numpy.zeros((npxls,),numpy.float32)


subapLocation=numpy.zeros((nsubaps,6),"i")
nsubapsCum=numpy.zeros((ncam+1,),numpy.int32)
ncentsCum=numpy.zeros((ncam+1,),numpy.int32)
for i in range(ncam):
    nsubapsCum[i+1]=nsubapsCum[i]+nsub[i]
    ncentsCum[i+1]=ncentsCum[i]+subapFlag[nsubapsCum[i]:nsubapsCum[i+1]].sum()*2

# now set up a default subap location array...
#this defines the location of the subapertures.
subx=(npxlx-16*camPerGrab)/nsubx
suby=(npxly-16)/nsuby
xoff=[8]*ncam
yoff=[8]*ncam
for k in range(ncam):
    nc=camPerGrab[k]
    for i in range(nsuby[k]):
        for j in range(nsubx[k]):
            indx=nsubapsCum[k]+i*nsubx[k]+j
            if subapFlag[indx]:
                subapLocation[indx]=(yoff[k]+i*suby[k],yoff[k]+i*suby[k]+suby[k],1,xoff[k]*nc+j/nc*subx[k]*nc+j%nc,xoff[k]*nc+j/nc*subx[k]*nc+subx[k]*nc+j%nc,nc)

pxlCnt=numpy.zeros((nsubaps,),"i")
# set up the pxlCnt array - number of pixels to wait until each subap is ready.  Here assume identical for each camera.
for k in range(ncam):
    # tot=0#reset for each camera
    for i in range(nsub[k]):
        indx=nsubapsCum[k]+i
        n=(subapLocation[indx,1]-1)*npxlx[k]+subapLocation[indx,4]
        pxlCnt[indx]=n
#pxlCnt[-5]=128*256
#pxlCnt[-6]=128*256
#pxlCnt[nsubaps/2-5]=128*256
#pxlCnt[nsubaps/2-6]=128*256

#The params are dependent on the interface library used.
cameraParams=numpy.zeros((7*ncam+4,),numpy.int32)
cameraParams[0]=1#affin elsize
cameraParams[1:7*ncam+1:7]=128*8#blocksize
cameraParams[2:7*ncam+1:7]=1000#timeout/ms
cameraParams[3:7*ncam+1:7]=range(ncam)#port
cameraParams[4:7*ncam+1:7]=2#thread 
cameraParams[5:7*ncam+1:7]=[1]+[0]*(ncam-1)#reorder pixels
cameraParams[6:7*ncam+1:7]=[0]+[2]*(ncam-1)#testLastPixel
cameraParams[7:7*ncam+1:7]=-1#affin
cameraParams[-3]=0#resync
cameraParams[-2]=1#wpu correction
cameraParams[-1]=2#number of frames to skip after short (truncated) frame.
centroiderParams=None
rmx=numpy.zeros((nacts,ncents)).astype("f")#FITS.Read("rmxRTC.fits")[1].transpose().astype("f")

mirrorParams=numpy.zeros((4,),"i")
mirrorParams[0]=1000#timeout/ms
mirrorParams[1]=2#port
mirrorParams[2]=-1#thread affinity
mirrorParams[3]=3#thread prioirty

control={
    "switchRequested":0,#this is the only item in a currently active buffer that can be changed...
    "pause":0,
    "go":1,
    "maxClipped":nacts,
    "refCentroids":None,
    "centroidMode":"CoG",#whether data is from cameras or from WPU.
    "windowMode":"basic",
    "thresholdAlgo":1,
    "reconstructMode":"simple",#simple (matrix vector only), truth or open
    "centroidWeight":None,
    "v0":numpy.ones((nacts,),"f")*32768,#v0 from the tomograhpcic algorithm in openloop (see spec)
    "bleedGain":0.0,#0.05,#a gain for the piston bleed...
    "actMax":numpy.ones((nacts,),numpy.uint16)*65535,#4095,#max actuator value
    "actMin":numpy.zeros((nacts,),numpy.uint16),#4095,#max actuator value
    "nacts":nacts,
    "ncam":ncam,
    "nsub":nsub,
    #"nsubx":nsubx,
    "npxly":npxly,
    "npxlx":npxlx,
    "ncamThreads":ncamThreads,
    "pxlCnt":pxlCnt,
    "subapLocation":subapLocation,
    "bgImage":bgImage,
    "darkNoise":darkNoise,
    "closeLoop":1,
    "flatField":flatField,#numpy.random.random((npxls,)).astype("f"),
    "thresholdValue":0.,#could also be an array.
    "powerFactor":1.,#raise pixel values to this power.
    "subapFlag":subapFlag,
    "fakeCCDImage":fakeCCDImage,
    "printTime":0,#whether to print time/Hz
    "rmx":rmx,#numpy.random.random((nacts,ncents)).astype("f"),
    "gain":numpy.ones((nacts,),"f"),
    "E":numpy.zeros((nacts,nacts),"f"),#E from the tomoalgo in openloop.
    "threadAffinity":None,
    "threadPriority":numpy.ones((ncamThreads.sum()+1,),numpy.int32)*10,
    "delay":0,
    "clearErrors":0,
    "camerasOpen":1,
    "cameraName":"libsl240Int32cam.so",#"camfile",
    "cameraParams":cameraParams,
    "mirrorName":"libmirrorSL240.so",
    "mirrorParams":mirrorParams,
    "mirrorOpen":0,
    "frameno":0,
    "switchTime":numpy.zeros((1,),"d")[0],
    "adaptiveWinGain":0.5,
    "corrThreshType":0,
    "corrThresh":0.,
    "corrFFTPattern":None,#correlation.transformPSF(correlationPSF,ncam,npxlx,npxly,nsubx,nsuby,subapLocation),
#    "correlationPSF":correlationPSF,
    "nsubapsTogether":1,
    "nsteps":0,
    "addActuators":0,
    "actuators":None,#(numpy.random.random((3,52))*1000).astype("H"),#None,#an array of actuator values.
    "actSequence":None,#numpy.ones((3,),"i")*1000,
    "recordCents":0,
    "pxlWeight":None,
    "averageImg":0,
    "slopeOpen":1,
    "slopeParams":centroiderParams,
    "slopeName":"librtcslope.so",
    "actuatorMask":None,
    "dmDescription":dmDescription,
    "averageCent":0,
    "calibrateOpen":1,
    "calibrateName":"librtccalibrate.so",
    "calibrateParams":None,
    "corrPSF":None,
    "centCalData":None,
    "centCalBounds":None,
    "centCalSteps":None,
    "figureOpen":0,
    "figureName":"figureSL240",
    "figureParams":numpy.array([1000,3,0xffff,2]).astype("i"),#timeout,port,affinity,priority
    "reconName":"libreconmvm.so",
    "fluxThreshold":0,
    "printUnused":1,
    "useBrightest":0,
    "figureGain":1,
    "decayFactor":None,#used in libreconmvm.so
    "reconlibOpen":1,
    "maxAdapOffset":0,
    "version":" "*120,
    #"lastActs":numpy.zeros((nacts,),numpy.uint16),
    }

#control["pxlCnt"][-3:]=npxls#not necessary, but means the RTC reads in all of the pixels... so that the display shows whole image
