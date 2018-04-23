*** Settings ***
Library           OperatingSystem
Library           String

*** Variables ***

${N_sample}   


*** Test Cases ***

Read_Text
    Example_Create_Use_file
	Config_plot

 

*** Keywords ***

Example_Create_Use_file
    Create File  c:/MKSInstruments/robotframework/EcatMFC/Examples/Output_files/varables_A.txt
    ${File}=    Get File    c:/MKSInstruments/robotframework/EcatMFC/Examples/Input_files/Inputs.txt
	Log To Console    \nGets the data in the file logs it to the console\n${File}
	Log To Console    \nEnd of the data in the file\n 
    @{list}=    Split to lines    ${File}
    Log To Console    Splits the Data in to lines and makes a list: @{list}\n	
	Log To Console    Starts the For Loop and commpares the # of lines to list when it reaches the end it exits\n
    :FOR    ${line}    IN    @{list}
    \   Log To Console    Data is assign to a seperate line ${line}
    \   ${Value}=    Get Variable Value  ${line}
    \   Set Global Variable    ${Value}    ${Value}
    \   Log To Console    Gets the data from the line and assigns it to a global variable called value:${Value}
    \   Sleep    1s
    \   write_variable_A
    
	 
write_variable_A
          :FOR    ${i}    IN RANGE    999999
    \    Exit For Loop If    ${i} == 100
    \    ${N_sample}=    Evaluate    ${N_sample} + 1
	\    Set Global Variable    ${N_sample}    ${N_sample}
    \    Append To File  c:/MKSInstruments/robotframework/EcatMFC/Examples/Output_files/varables_A.txt  ${N_sample} , ${Value}\r\n\r\n 	

Config_plot
    ${frt}=     Run    c:/Python27/Test_plot.py    
    Log To Console     \n[${frt}]  	
    
