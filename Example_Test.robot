*** Settings ***
Library           OperatingSystem
Library           String
Library           BuiltIn




*** Test Cases ***

Example_Start_Test 
   _Test   


*** Keywords ***




_Test
    :FOR    ${i}    IN RANGE    999999
    \    Exit For Loop If    ${i} == 1
	\    Run Example1
    \    Log To Console    _Test loopcount ${i}
	   
 

	


Run_Example1
    ${frt}=     Run    pybot --outputdir c:/MKSInstruments/robotframework/EcatMfc/Output/Example1_readfromtextfile_output c:/MKSInstruments/robotframework/EcatMFC/Examples/Scripts/Example1_.robot
    Log To Console      ${frt}	  	