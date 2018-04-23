# This program prints the plot!
import matplotlib.pyplot as plt
plt.axis([0, 1000, 0, 1000])
import numpy as np


x, y = np.loadtxt('c:/MKSInstruments/robotframework/EcatMFC/Output/setpoint_variable.txt', delimiter=',', unpack=True)
plt.plot(x,y, label='Loaded from file setpoitn_variable.txt')

plt.xlabel('Samples')
plt.ylabel('Setpoint sccm')
plt.title('Setpoint')
plt.legend() 
plt.savefig('c:/MKSInstruments/robotframework/EcatMFC/Plot/setpoint.png')  
#plt.show() 
plt.close()
