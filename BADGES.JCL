//YOURJOB JOB &SYSUID,'Badge Updater',MSGCLASS=H,CLASS=A,REGION=0M
//STEP1 EXEC PGM=BPXBATSL,PARM='PGM &PY &PR/update_directory_badges.py'
// SET PY='/usr/lpp/IBM/cyp/v3r8/pyz/bin/python3' // Path to Python interpreter
// SET PR='/u/&SYSUID/python_scripts' // Path to your Python script directory
//STDOUT DD SYSOUT=*
//STDERR DD SYSOUT=*
//SYSDUMP DD SYSOUT=*
//CEEDUMP DD SYSOUT=*
//STDIN DD DUMMY