#!/usr/bin/env python3
import numpy as np
import time
from fluidlab.daq.daqmx import read_analog
from zaber_motion import Units
from zaber_motion.ascii import Connection
from datetime import datetime
from pynput import keyboard
from pynput.keyboard import Key

def on_press(key):
    if key == keyboard.Key.up:
        try:
            axis.move_relative(+1, Units.LENGTH_MILLIMETRES)
        except:
            pass
    if key == keyboard.Key.down:
        try:
            axis.move_relative(-1, Units.LENGTH_MILLIMETRES)
        except:
            pass
    if key == keyboard.Key.esc:
        listener.stop()

class probe:
    def __init__(self,port,center,top,bot,X,Y):
        """
        port : connection port of the zaber, usually COM7
        center : center poistion of the tank.
        top : top position where you want the probe to start
        bot : bottom position where you want the probe to stop.
        X : X position for a moving prob on X axis. Usufull for radial compoenent.
        Y : Y position for a moving prob on X axis. Usufull for radial compoenent.
        """
        self.port = port
        self.center = center
        self.top = top
        self.bot = bot
        self.X = X
        self.Y = Y

    def centering(self,manual=False):
        """
        Center the prob according to the center value, if not centered, use .centering(manual=True) to do it yourself.
        """
        with Connection.open_serial_port(self.port) as connection:
            device_list = connection.detect_devices()
            print("Found {} devices".format(len(device_list)))
            device = device_list[0]
            axis = device.get_axis(1)
            try:
                axis.move_absolute(self.center, Units.LENGTH_MILLIMETRES)
            except:
                pass
            if manual == True:
                print("Use up and down arrow to move the prob. Press escape to exit.")
                with keyboard.Listener(on_press=on_press) as listener:
                    listener.join()
                self.center = axis.get_position(Units.LENGTH_MILLIMETRES)
    
    def sauvegarde(self,coils,parameters,Data):
        """
        saving function just to avoid writing it everytime.
        """
        np.savetxt(parameters.path + "_"+datetime.now().strftime("%Y-%m-%d_%H:%M")+".txt",Data,delimiter=",")
        np.save(parameters.path + "_"+datetime.now().strftime("%Y-%m-%d_%H:%M"),Data)
        with open(parameters.path + "_setup_"+datetime.now().strftime("%Y-%m-%d_%H:%M")+".txt", "w") as f:
            f.write("--- Calibration --- \n")
            f.write("Path to data : \n")
            f.write(parameters.path + "_"+datetime.now().strftime("%Y-%m-%d_%H:%M")+".txt \n")
            f.write(parameters.path + "_"+datetime.now().strftime("%Y-%m-%d_%H:%M")+".npy \n")
            f.write("--- Experimental setup ---\n")
            for k in range(len(coils.current)):
                f.write("Z_"+str(k+1)+" = "+str(coils.position[k])+" mm ;I_"+str(k+1)+" = "+str(coils.current[k])+"A \n")
                f.write("Probe position : X = "+str(self.X)+" Y ="+str(self.Y))

    def operate(self,coils,parameters):
        """
        Measure the field in x,y,z directions while moving on z.
        """
        Data = np.zeros((parameters.N,4))
        with Connection.open_serial_port(self) as connection:
            device_list = connection.detect_devices()
            print("Found {} devices".format(len(device_list)))
            device = device_list[0]
            axis = device.get_axis(1)
            try:
                axis.move_absolute(self.top, Units.LENGTH_MILLIMETRES)
            except:
                pass
            
            while axis.is_busy() == True:
                time.sleep(1)
                print("Waiting for the stage to be in position...")
            print("In position.")
            for k in range(parameters.N):
                print(k/parameters.N)
                Data[k,1], Data[k,2], Data[k,3] = parameters.rng*np.mean(read_analog(("Dev5/ai0", "Dev5/ai1", "Dev5/ai2"),
                    terminal_config="Diff", volt_min=-5, volt_max=5, samples_per_chan=int(parameters.fe*parameters.tau), sample_rate=parameters.fe),axis = 1)
                Data[k,0] = axis.get_position(Units.LENGTH_MILLIMETRES) #in mm 
                time.sleep(parameters.tau)
                try:
                    axis.move_relative(-parameters.deltax, Units.LENGTH_MILLIMETRES)
                except:
                    pass
                while axis.is_busy() == True:
                    time.sleep(1)
            
            if parameters.save == True:
                self.sauvegarde(coils,parameters,Data)


class coils:
    def __init__(self,I,Z):
        """
        I : Array of the currents in the coils
        Z : Array of the positions of the coils
        """
        self.current = I
        self.position = Z

class parameters:
    def __init__(self, tau, fe, range, N, x, save, path):
        """
        tau : Acquisition time
        fe : Acquisition frequency
        range : range of the gaussmeter, in gauss per volt (usually 100 G/V)
        N : Number of point you want
        x : lenght in mm of the area to make measurements.
        save : Boolean, for saving value or not.
        path : path to folder where to save.
        """
        self.tau = tau 
        self.fe = fe
        self.rng = range
        self.N = N
        self.x = x
        self.deltax = x/N
        self.save = save
        self.path = path
        
if __name__ == "__main__":
        prb = probe(port="COM7",
                    center=98,
                    top=250,
                    bot=30,
                    X=068.3,
                    Y=951.3)
        cls = coils(I=np.array([4.0,  0.5,  3.58,     -0.3,   -0.5,   -4.86]),
                    Z=np.array([26.5,   24.5,  12.0,   -12.0,  -24.5,  -26.5]))
        settings = parameters(tau=2,
                              fe=10000,
                              range=300/3,
                              N=100,
                              x=220,
                              save=True,
                              path="C:/Users/Gsu/Desktop/SDT_EXP/calibration"
        )
