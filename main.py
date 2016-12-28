#!/bin/python3

import articlelib
import getpass, getopt, sys


username = None
password = None
b = articlelib.blndl()

try:
    opt, args = getopt.getopt(sys.argv[1:], "u:p:")
    for o,a in opt:
        if(o == "-u"):
            username = a
            print(username)
        elif(o == "-p"):
            password = a
except getopt.GetoptError as e:
    print("You can pass username (-u) and password (-p) on commandline.\nYour password will be promt on the console!!!")


if(username == None):
    print("Please login to blendle.com")
    print("Username/Mail: ")
    username = input()
if(password == None):
    password = getpass.getpass()

b.login(username, password)
if(b._loggedin == True):
    print("balance: ", b._loginresponse["_embedded"]["user"]["balance"])
    print("reads: ", b._loginresponse["_embedded"]["user"]["reads"])
    b.loadArticles(onlyLatestArticle=True)
    print("Loaded {0} articles!".format(len(b._items)))
    #b.listArticles()
    #print("Index of article you want to see: ")
    #i = input()
    #b.showArticle(int(i))
    b.downloadArticle(4, "~/read")
    b.logout()
