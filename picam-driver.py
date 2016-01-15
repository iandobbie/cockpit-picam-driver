#V 1.0 IMD 29160113
#adapted from mickp/FlyCapture2-ctypes on github to have a softcamera on a
#RaspberryPi for cockpit.
#
# Copyright Ian Dobbie <ian.dobbie@bioch.ox.ac.uk>
# Mick Phillips <mick.phillips@diamond.ac.uk>
# 2016
#
import decimal
import numpy as np
import Pyro4
import signal
import sys
import threading
import time
import picamera
from io import BytesIO

#to enable control of the camera LED
import RPi.GPIO as GPIO


Pyro4.config.SERIALIZER = 'pickle'
Pyro4.config.SERIALIZERS_ACCEPTED.add('pickle')

MAX_STRING_LENGTH = 512

class Camera(object):
    def __init__(self):
        self.camera = None
        self.guid = None
        self.cameraInfo = None
        self.connected = False
        self.client = None
        self.lastImage = None
        self.imgRaw = None
        self.width = 512
        self.height = 512
        
        
    def __del__(self):
        c = self.camera
        if not c:
            return
#        try:
#            #no current shutdown instructions
#        except:
#            pass


    def connect(self, index=0):
        if not self.camera:
            self.camera  = picamera.PiCamera()
        if not self.camera:
            raise Exception('No camera found.')

        #picam setup
        #set max resolutioon for still capture
        self.camera.resolution = (self.width, self.height)
        # use string CAMERA_RESOLUTION to get max resolution
        self.connected = True
        #disable camera LED by default
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(5, GPIO.OUT, initial=False)

        

    def enableCamera(self):
        if not self.connected: self.connect()
        return True


    def disableCamera(self):
        if not self.connected or not self.camera:
            return
        self.camera.close()
        return False


    def grabImageToDisk(self, outFileName='picam-Test.png'):
        stream = BytesIO()
        self.camera.capture(stream,format='yuv')
        stream.seek(0)
        open(outFileName, 'wb').write(stream.getvalue())
       

    
    def grabImageToBuffer(self):
        #setup stream, numpy from file only acepts a real file so....
        stream = open('image.data', 'w+b')
        #grab yuv image to stream
        self.camera.capture(stream,format='yuv')
        #seek back to start of stream
        stream.seek(0)
        #pull out the Y channel (luminessence) as 8 bit grey
        imgConv = np.fromfile(stream, dtype=np.uint8,
                              count=self.width*self.height).reshape((self.height,
                                                                     self.width))
          self.lastImage = imgConv

    def getImageSize(self):
        width, height = self.width, self.height
        return (int(width), int(height))


    def getImageSizes(self):
        return [self.width,self.height]


    def getTimeBetweenExposures(self, isExact=False):
        if isExact:
            return decimal.Decimal(0.1)
        else:
            return 0.1


    def getExposureTime(self, isExact=False):
        if isExact:
            return decimal.Decimal(0.1)
        else:
            return 0.1


    def setExposureTime(self, time):
        pass


    def setImageSize(self, size):
        pass

    def setLED(self, state=False):
        GPIO.output(5, state)
    
    def softTrigger(self):
        if self.client is not None:
            self.grabImageToBuffer()
            self.client.receiveData('new image',
                                     self.lastImage,
                                     time.time())


    def receiveClient(self, uri):
        """Handle connection request from cockpit client."""
        if uri is None:
            self.client = None
        else:
            self.client = Pyro4.Proxy(uri)


def main():
    print sys.argv
    host = '10.0.0.2' or sys.argv[1]
    port = 8000 or int(sys.argv[2])
    daemon = Pyro4.Daemon(port=port, host=host)

    # Start the daemon in a new thread so we can exit on ctrl-c
    daemonThread = threading.Thread(
        target=Pyro4.Daemon.serveSimple,
        args = ({Camera(): 'pyroCam'},),
        kwargs = {'daemon': daemon, 'ns': False}
        )
    daemonThread.start()

    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break

    daemon.shutdown()
    daemonThread.join()


if __name__ == '__main__':
    main()
