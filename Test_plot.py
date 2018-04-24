# This program prints the plot!
import matplotlib.pyplot as plt
plt.axis([0, 1000, 0, 1000])
import numpy as np

x, y = np.loadtxt('c:/MKSInstruments/robotframework/EcatMFC/Examples/Output_files/varables_A.txt', delimiter=',', unpack=True)
plt.plot(x,y, label='varables_A.txt')

plt.xlabel('Samples')
plt.ylabel('Flow sccm')
plt.title('Flow')
plt.legend() 
plt.savefig('c:/MKSInstruments/robotframework/EcatMFC/Examples/Output_files/Test.png')  
plt.show() 
plt.close()
