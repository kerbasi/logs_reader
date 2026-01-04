import re
import time

from subprocess import PIPE,Popen
import os


import functools


class bcolors:
    OKBLUE = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

my_sn  = input(bcolors.BOLD+"insert SN: "+bcolors.ENDC)


try:
    with open('/usr/flexfs/qms3/site.ws', 'r') as f:
        site = f.read().strip()
except IOError as e:
    print(f"Error reading site file: {e}")


curl_d = "curl -d "
sn = '{"SN":"%s"}' % my_sn
new_sn = "'%s'" % sn
H = " -H"
Content = ' "Content-Type: application/json"'
post = f" -X POST http://{site}/OperationServices/Product/Get_ProductPN"

os.system("%s %s %s %s %s >/usr/flexfs/users/loayk/file_loay.txt" % (curl_d, new_sn, H, Content, post))


pn_list = []
list_split = []

P0 = Popen(["cat","/usr/flexfs/users/loayk/file_loay.txt"], stdout=PIPE)
for i in P0.stdout:
    list_split.append(i)
    
P0.terminate()

my_split = str(list_split[0])
my_new_split = (my_split.split(":")[3].split(",")[0])
print(my_new_split[1:-1])
print(my_sn)
my_new_split = my_new_split[1:-1]


#with open("/tmp/file.txt", "r") as sn_txt:
#    for i in sn_txt:
#        pattern1 = re.compile("S\D+\d+")
#        match1 = pattern1.findall(str(i))
#
#        if match1:
#            pn_list.append(match1[0])
#    sn_txt.close()






list_year = ["2022", "2023","2024","2025"]
list_i = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]

my_new_dic = {}

print("\n")
index = 0
sn_log = []


for j in list_year:

    for i in list_i:
	
        x = os.path.exists("/usr/flexfs/lion_cub/log/ft/%s/%s%s/%s.mlnx" % (my_new_split,j,i, my_new_split))
        if x:
            os.system("cat /usr/flexfs/lion_cub/log/ft/%s/%s%s/%s.mlnx | grep %s" % (my_new_split,j, i, my_new_split, my_sn))
            os.system(
                "ls -ltr /usr/flexfs/lion_cub/log/ft/%s/%s%s/DEBUG | grep %s > /tmp/file_log.txt" % (my_new_split,j,i, my_sn))

            # sn_log = []
            # index = 0
            with open("/tmp/file_log.txt", "r") as sn:
                for jj in sn:
                    pattern1 = re.compile("\d+\S+.gz")
                    match1 = pattern1.findall(str(jj))

                    if match1:
                        sn_log.append(match1[0])
                        index += 1
                        my_new_dic[index] = "/usr/flexfs/lion_cub/log/ft/%s/%s%s/DEBUG/%s" % (
                        my_new_split,j,i, sn_log[index - 1])
                        print("\n")
                        print("%s  -  %s" % (index,
                                             (bcolors.BOLD + "/usr/flexfs/lion_cub/log/ft/%s/%s%s/DEBUG/%s" + bcolors.ENDC) % (
                                             my_new_split, j,i, sn_log[index - 1])))

            sn.close


        x = os.path.exists("/usr/flexfs/lion_cub/log/%s/%s%s/%s.mlnx" % (my_new_split,j,i, my_new_split))
        if x:
            os.system("cat /usr/flexfs/lion_cub/log/%s/%s%s/%s.mlnx | grep %s" % (my_new_split,j, i, my_new_split, my_sn))
            os.system(
                "ls -ltr /usr/flexfs/lion_cub/log/%s/%s%s/DEBUG | grep %s > /tmp/file_log.txt" % (my_new_split,j,i, my_sn))

            # sn_log = []
            # index = 0
            with open("/tmp/file_log.txt", "r") as sn:
                for jj in sn:
		    
                    pattern1 = re.compile("\d+\S+.gz")
                    match1 = pattern1.findall(str(jj))

                    if match1:
                        sn_log.append(match1[0])
                        index += 1
                        my_new_dic[index] = "/usr/flexfs/lion_cub/log/%s/%s%s/DEBUG/%s" % (
                        my_new_split,j,i, sn_log[index - 1])
                        print("\n")
                        print("%s  -  %s" % (index,
                                             (bcolors.BOLD + "/usr/flexfs/lion_cub/log/%s/%s%s/DEBUG/%s" + bcolors.ENDC) % (
                                             my_new_split, j,i, sn_log[index - 1])))

            sn.close
	


        x = os.path.exists("/usr/flexfs/lion_cub/log/customization/%s/%s%s/%s.mlnx" % (my_new_split,j,i, my_new_split))
        if x:
            os.system("cat /usr/flexfs/lion_cub/log/customization/%s/%s%s/%s.mlnx | grep %s" % (my_new_split,j, i, my_new_split, my_sn))
            os.system(
                "ls -ltr /usr/flexfs/lion_cub/log/customization/%s/%s%s/DEBUG | grep %s > /tmp/file_log.txt" % (my_new_split,j,i, my_sn))

            # sn_log = []
            # index = 0
            with open("/tmp/file_log.txt", "r") as sn:
          	

		#sn_read = sn.read()
		#print(sn_read)
                for jj in sn:
                    pattern1 = re.compile("\S+\d+\S+.gz")
                    match1 = pattern1.findall(str(jj))

                    if match1:
                        sn_log.append(match1[0])
                        index += 1
                        my_new_dic[index] = "/usr/flexfs/lion_cub/log/customization/%s/%s%s/DEBUG/%s" % (
                        my_new_split,j,i, sn_log[index - 1])
                        print("\n")
                        print("%s  -  %s" % (index,
                                             (bcolors.BOLD + "/usr/flexfs/lion_cub/log/customization/%s/%s%s/DEBUG/%s" + bcolors.ENDC) % (
                                             my_new_split, j,i, sn_log[index - 1])))

            sn.close





if len(sn_log) ==0:
    print("NO log found !!!")
    exit()    

print("\n")

#print(my_new_dic)
#print(my_new_dic.keys())

my_list_keys = [str(i) for i in my_new_dic.keys()]


#countdown(10)



#def countdown(t):

#    while t:
#        mins, secs = divmod(t, 60)
#        timer = '{:02d}:{:02d}'.format(mins, secs)
#        #print(timer, end="\r")
#       time.sleep(1)
#        t -= 1
#
#    exit("time out\n")





#while True: 
#    my_log_number = input(bcolors.BOLD+"insert log number or q for exit: \n"+bcolors.ENDC)
#
#    if my_log_number not in my_list_keys:
#        if my_log_number == "q":
#            print("\n")
#            print(bcolors.BOLD+" !!!!!!!!!!Thank You !!!!!!!!!!"+bcolors.ENDC)
#            print("\n")
#            exit()
#
#        print("number log not exsist")
#    elif my_log_number in my_list_keys:
#        os.system("less -r %s "% my_new_dic[int(my_log_number)])


#countdown(10)

while True:

    my_log_number = input("insert log number or q for exit:")

    if my_log_number not in my_list_keys:
        if my_log_number == "q":
            print("\n")
            print(bcolors.BOLD + " !!!!!!!!!!Thank You !!!!!!!!!!" + bcolors.ENDC)
            print("\n")
            exit()
        else:
            print("number log not exsist")
    if my_log_number in my_list_keys:
        os.system("less -r %s " % my_new_dic[int(my_log_number)])
