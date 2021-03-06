# chatproxy
connects to sbs chat and serves in its stead (persistent session, multiple clients at once)
## requirements
- python 3.4+
- websockets library
## how to use in smilebasicsource.com/chat (special thanks to 12)
 1. modify the addresses in main.py as you see fit (lines 12 and 102)
 2. add this to your [chatJS](https://smilebasicsource.com/editor?type=chat):
```
if(hasSpecial("socketOverload")){
    polyChat.onClose=onClose;
    polyChat.onError=onError;
    polyChat.onMessage=onMessage;
    polyChat.webSocketURL = "ws://127.0.0.1:8765";
    polyChat.start(document.getElementsByTagName('body')[0].getAttribute('data-uid'),document.getElementsByClassName('chat')[0].getAttribute('data-chatauth'))
    activePingId=window.setInterval(activePing,45000);
    window.addEventListener('focus',activePing);
}
```
 3. add "socketOverload" to your [special field](https://smilebasicsource.com/userhome)
 4. modify the second to last line of main.py and the webSocketURL in the chatJS to match and fit your situation
 
 4a. this means that you might have to change line 163 `websockets.serve(handler,"localhost",8765)` to `websockets.serve(handler,port=8765)`
## what it does
it holds a connection with sbs chat and serves it to chat clients, even multiple at once.  
regular chat clients can connect to this by changing the address they connect to, which is what the setup above does.
