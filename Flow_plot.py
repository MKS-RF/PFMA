# This program prints the plot!
import matplotlib.pyplot as plt
plt.axis([0, 1000, 0, 1000])
import numpy as np

x, y = np.loadtxt('c:/MKSInstruments/robotframework/EcatMFC/Output/flow_variable.txt', delimiter=',', unpack=True)
plt.plot(x,y, label='Loaded from flow_variable.txt')

plt.xlabel('Samples')
plt.ylabel('Flow sccm')
plt.title('Flow')
plt.legend() 
plt.savefig('c:/MKSInstruments/robotframework/EcatMFC/Plot/Flow.png')  
#plt.show() 
plt.close()
