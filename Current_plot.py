# This program prints the plot!
import matplotlib.pyplot as plt
plt.axis([0, 1000, 0, 70])
import numpy as np

x, y = np.loadtxt('c:/MKSInstruments/robotframework/EcatMFC/Output/current_variable.txt', delimiter=',', unpack=True)
plt.plot(x,y, label='Loaded from file current_variable.txt')

plt.xlabel('Samples')
plt.ylabel('Current_ma')
plt.title('Current')
plt.legend() 
plt.savefig('c:/MKSInstruments/robotframework/EcatMFC/Plot/current.png')  
#plt.show() 
plt.close()
