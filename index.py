import asyncio
import websockets
import json
import os
import signal
import logging
import time

logfmt = '%(asctime)s - %(levelname)s - %(message)s'
loghdlrs = [logging.FileHandler('index.log'), logging.StreamHandler()]
logging.basicConfig(level=logging.INFO, format=logfmt, handlers=loghdlrs)
logging.basicConfig(level=logging.ERROR, format=logfmt, handlers=loghdlrs)
logging.basicConfig(level=logging.CRITICAL, format=logfmt, handlers=loghdlrs)

if os.getenv('IDEBUG') == True:
    logging.basicConfig(level=logging.DEBUG)

class WSS:
    def __init__(self):
        self.STATE = 0
        self.WSS_PORT = 2112

        self.UID_SOCK = dict()
        self.ADDR_UID = dict()

    async def start(self, stop):
        async with websockets.serve(self.ws, '0.0.0.0', self.WSS_PORT):
            logging.info(f'Starting server on {self.WSS_PORT} port')
            await stop

    async def checkuser(self, user, asker, sock):
        if user in self.ADDR_UID:
            msg = {
                'm': 'get',
                'q': 'you',
                'u': asker
            }

            jmsg = json.dumps(msg)
            logging.info(f'> {jmsg}')
            await self.UID_SOCK[self.ADDR_UID[user]].send(jmsg)
        else:
            res = {
                'm': 'info',
                'q': 'checkuser',
                'u': user,
                'c': 404,
            }
            jres = json.dumps(res)
            logging.info(f'> {jres}')
            await sock.send(jres)

    async def senduser(self, asker, name, status):

        if asker in self.UID_SOCK: 

            res = {
                'm': 'info',
                'q': 'checkuser',
                'c': 200,
                'res': {
                    'name': name,
                    'status': status
                }
            }
            jres = json.dumps(res)
            logging.info(f'> {jres}')
            await self.UID_SOCK[asker].send(jres)

    async def sendmsg(self, addr, sender, ts, pack):
        if addr in self.ADDR_UID:

            msg = {
                'm': 'put',
                'q': 'msg',
                'user': sender,
                'pack': pack
            }
            jmsg = json.dumps(msg)
            logging.info(f'> {jmsg}')
            await self.UID_SOCK[self.ADDR_UID[addr]].send(jmsg)

            c = 200
            #await asyncio.wait([self.USER_SOCK[_user].send(jmsg) for _user in self.PUB_USER[pub]])
        else:
            c = 404

        res = {
            'm': 'info',
            'q': 'sendmsg',
            'd': ts,
            'c': c,
            'pack': pack
        }
        return json.dumps(res)

    async def checkin(self, uid, sock, addr):

        if addr in self.ADDR_UID:
            c = 409
        else:
            self.ADDR_UID.update({addr: uid})
            c = 201

        res = f'{{"m": "info", "q": "checkin", "c": {c}}}'

        logging.info(f'CHECKIN {addr} {uid}')

        return res

    async def checkout(self, addr):

        if addr in self.ADDR_UID:
            self.ADDR_UID.pop(addr, None)
            logging.info(f'CHECKOUT {addr}')
        else:
            pass     

    async def ws(self, SOCK, path=None):

        UID = int(time.time() * 1000)
        self.UID_SOCK.update({UID: SOCK})
        logging.info(f'OPEN CONNECTION FROM {UID}')

        ADDR = str()

        res = {
            'm': "info", 
            'q': "srv", 
            'c': 100, 
            'res' : {
                'pub': "123123123",
                'uid': UID,
                'online': len(self.UID_SOCK)
            }
        }

        await SOCK.send(json.dumps(res))

        try:
            async for sock in SOCK:
                #print(websocket.closed)
                #print(websocket.open)
                req = json.loads(sock)
                logging.info(f'< {req}')
                method = req['m']
                query = req['q']
                #print (locals())

                if method == 'put':

                    if query == 'user':
                        ADDR = req['pack']['addr']
                        res = await self.checkin(UID, SOCK, ADDR)
                        logging.info(f'> {res}')
                        await SOCK.send(res)

                    if query == 'msg':

                        if 'n' not in req:
                            req['n'] = 'Unknown'

                        if 'd' not in req:
                            req['d'] = int(time.time() * 1000)

                        if 'u' in req and 'pack' in req:
                            res = await self.sendmsg(req['u'], req['n'], req['d'], req['pack'])

                        else:
                            res = {
                                'm': 'info',
                                'q': 'sendmsg',
                                'd': req['d'],
                                'c': 400
                            }
                            
                        logging.info(f'> {res}')
                        await SOCK.send(res)        

                if method == 'get':

                    if query == 'user':
                        res = await self.checkuser(req['u'], UID, SOCK)

                if method == 'post':

                    if query == 'user':

                        if 'name' not in req:
                            req['name'] = 'Unknown'

                        if 'status' not in req:
                            req['status']= '~'

                        res = await self.senduser(req['u'], req['name'], req['status'])

        except Exception as e:
            logging.error(f'{type(e).__name__}: {e}')
            #cf01b7a83315db38b082e83cf7dbc1fb7fa73d9606f93211a13efba1ed510e07
        
        finally:
            self.UID_SOCK.pop(UID, None)
            await self.checkout(ADDR)
            logging.info(f'CLOSE CONNECTION FROM {UID}')
if __name__ == '__main__':
    try:
        ws = WSS()
        loop = asyncio.get_event_loop()

        stop = asyncio.Future()
        loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)

        server = loop.run_until_complete(ws.start(stop))
    except (KeyboardInterrupt, SystemExit):
        pass
