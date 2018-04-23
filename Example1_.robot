*** Settings ***
Library           OperatingSystem
Library           String




*** Test Cases ***

Read_Text
    Example_of_looping_over_the_lines_in_a_file 


 

*** Keywords ***

Example_of_looping_over_the_lines_in_a_file
    ${File}=    Get File    c:/MKSInstruments/robotframework/EcatMFC/Examples/Input_text_files/Inputs.txt
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
     