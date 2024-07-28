from fullGSapi.api import client

COURSE_ID = 782967 # CS10 Su24 course id
ASSIGNMENT_ID = 4486584 # CS10 Su24 lab2 assignment id

gradescope_client =  client.GradescopeClient()
gradescope_client.prompt_login()
assignment_scores = gradescope_client.download_scores(COURSE_ID, ASSIGNMENT_ID)
