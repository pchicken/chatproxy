#!/usr/bin/python
# chat proxy by chicken

#----------------
# authentication
#----------------
import sys
import hashlib
import json
import requests

url = "https://lumage.smilebasicsource.com"

# get session id
def getsession(username, password):
    print(username,password)
    response = requests.post(
        f"{url}/query/submit/login",
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

# get chatauth (and uid!)
def getchatauth(session):
    response = requests.get(
        f"{url}/query/request/chatauth",
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
        print("not enough auth info in file!") # i think this case doesn't save auth.txt
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
    #debug: ws://direct.smilebasicsource.com:45697/chatserver
    #main:  ws://direct.smilebasicsource.com:45695/chatserver
    uri = "ws://direct.smilebasicsource.com:45697/chatserver"
    async with websockets.connect(uri, ping_interval=None) as server:
        # bind
        message = json.dumps({"type":"bind","lessData":True,"uid":uid,"key":chatauth})
        await server.send(message)
        print(f"us:{message}")
        response = await server.recv()
        print(f"server:{response}")
        
        # communicate with server
        queuelist = [] # hold queues for sending back to client
        async def listenserver(): # send messages to clients
            print(f"listening on {uri}")
            while True:
                try:
                    received = await server.recv()
                    print(received)
                    for queue in queuelist:
                        await queue.put(received)
                except:
                    break
                    
        messages = asyncio.Queue() # to get messages from clients
        async def messageserver(): # forward messages to server
            while True:
                try:
                    message = await messages.get()
                    await server.send(message)
                except:
                    break
                    
        async def handler(websocket, path): # BE the server
            response = asyncio.Queue()
            queuelist.append(response)
            print("connected to client")
            message = await websocket.recv()
            bind = json.loads(message)
            if bind["key"] == chatauth:
                async def listenclient(): # send requests to server
                    await messages.put('{"type":"request","request":"userList"}')
                    await messages.put('{"type":"request","request":"messageList"}')
                    while True:
                        try:
                            received = await websocket.recv()
                            print(received)
                            await messages.put(received)
                        except:
                            break
                            
                async def sendclient(): # forward messages to client
                    while True:
                        try:
                            message = await response.get()
                            await websocket.send(message)
                        except:
                            break
                            
                await asyncio.gather(listenclient(),sendclient(),)
            queuelist.remove(response) # GOSH i hope this works, otherwise IM FUCKED>EDIT: it worked
            print("disconnected from client")
            
        await asyncio.gather(listenserver(), messageserver(), websockets.serve(handler,"localhost",8765))
        
asyncio.get_event_loop().run_until_complete(main(uid,chatauth))
