#!/usr/bin/python
# chat proxy by chicken

#----------------
# authentication
#----------------
import sys
import hashlib
import json
import requests

#get session id
def getsession(username, password):
    print(username,password)
    response = requests.post(
        "https://development.smilebasicsource.com/query/submit/login",
        params = {"session":"3"}, #put garbage in
        data = {
            "username":username,
            "password":password
            }
        )
    result = response.json()["result"]

    if result == False:
        sys.exit("auth info incorrect")

    return result

# use session id to get chatauth (and uid!)
def getchatauth(session):
    response = requests.get(
        "https://development.smilebasicsource.com/query/request/chatauth",
        params = {"session":session}
        )
    return response.json()

save = True # set to True if you want to save auth.txt
written = False
session = ""

# get login info from auth.txt
try:
    auth = open("auth.txt", "r")
    info = auth.readlines() # username, password (hash), session id
    username = info[0].rstrip() # trim newline
    password = info[1].rstrip()
    if len(info) > 2:
        session = info[2].rstrip()
        print("got previous session!")
    elif len(info) < 2 or username == "" or password == "":
        print("not enough auth info in file!") # p sure this also 
        username = input("username:")
        password = hashlib.md5(input("password:").encode()).hexdigest()
        
    # request session
    if len(info) < 3: # session id needed
        print(f"getting session as {username}")
        written = True
        session = getsession(username, password)
        
    auth.close()
except FileNotFoundError:
    print("auth.txt not found!")
    written = True
    username = input("username:")
    password = hashlib.md5(input("password:").encode()).hexdigest()
    

# get chatauth, and get new session if needed
response = getchatauth(session)
if response["requester"] == False:
    print(f"{session} session was bad!")
    written = True
    session = getsession(username, password)
    response = getchatauth(session)
    if response["requester"] == False:
        sys.exit("new session failed!")
        
if save and written: # write new info to auth.txt
    print("writing to auth.txt...")
    with open("auth.txt","w+") as auth:
        auth.write(username+"\n")
        auth.write(password+"\n")
        auth.write(session)
        
chatauth = response["result"]
uid = response["requester"]["uid"]
print(f"uid:{uid}\nkey:{chatauth}")

#-------------
# connections
#-------------
import asyncio
import websockets

async def main(uid,chatauth):
    uri = "ws://direct.smilebasicsource.com:45697/chatserver"
    async with websockets.connect(uri, ping_interval=None) as server:
        #bind
        message = json.dumps({"type":"bind","lessData":True,"uid":uid,"key":chatauth})
        await server.send(message)
        print(f"us:{message}")
        response = await server.recv()
        print(f"server:{response}")
        
        #
        queuelist = [] # hold queues for sending back to client
        async def listenserver(): # send messages to clients
            print(f"listening on {uri}")
            while True:
                message = await server.recv()
                print(message)
                for queue in queuelist:
                    await queue.put(message)
                    
        requests = asyncio.Queue() # to get requests from clients
        async def requestserver(): # forward requests to server
            while True:
                request = await requests.get()
                await server.send(request)
                
        async def handler(websocket, path): # be a server. i am speed.
            response = asyncio.Queue()
            queuelist.append(response)
            print("connected to client")
            message = await websocket.recv()
            bind = json.loads(message)
            if bind["key"] == chatauth:
                async def listenclient(): # send requests to server
                    await requests.put('{"type":"request","request":"userList"}')
                    await requests.put('{"type":"request","request":"messageList"}')
                    while True:
                        try:
                            await requests.put(await websocket.recv())
                        except websockets.exceptions.ConnectionClosedError:
                            break
                            
                async def sendclient(): # forward messages to client
                    while True:
                        try:
                            await websocket.send(await response.get())
                        except websockets.exceptions.ConnectionClosedError:
                            break
                            
                await asyncio.gather(listenclient(),sendclient(),)
            queuelist.remove(response) # GOSH i hope this works, otherwise IM FUCKED>EDIT: it worked
            print("disconnected from client")
            print(queuelist)
        await asyncio.gather(
            listenserver(), requestserver(),
            websockets.serve(handler,"localhost",8765)
            )
        
asyncio.get_event_loop().run_until_complete(main(uid,chatauth))
