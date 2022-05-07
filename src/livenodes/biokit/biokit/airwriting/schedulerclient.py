import threading
import queue
import time

import argparse
import zmq
from . import scheduler
import pprint


class ZmqClient(threading.Thread):

    def __init__(self, host="localhost", port=8888):
        threading.Thread.__init__(self, name='ZmqClient')
        self.toClient = queue.Queue()
        self.fromClient = queue.Queue()
        self.context = zmq.Context()
        self.zmqsocket = self.context.socket(zmq.REQ)
        serverurl = 'tcp://' + host + ':' + str(port)
        print(("connecting with server at: " + serverurl))
        self.zmqsocket.connect(serverurl)

    def sendCommand(self, command, data):
        self.fromClient.put({'command': command, 'data': data})
        response = self.toClient.get()
        return response

    def getMachineConf(self):
        return self.sendCommand("MACHINEINFO", None)

    def setMachineConf(self, machineconf):
        return self.sendCommand("MACHINECONF", machineconf)

    def killScheduler(self):
        return self.sendCommand("EXIT", None)

    def delMachine(self, hostname):
        mconf = self.getMachineConf()
        if hostname in list(mconf.keys()):
            del mconf['hostname']
            re = self.setMachineConf(mconf)
            print(("New machine conf: " + str(re)))
            return re
        else:
            print("Machine is not in conf, nothing to do...")
            return mconf

    def changeMachine(self, hostname, maxcore=None, minfreecore=None):
        mconf = self.getMachineConf()
        mconf[hostname]['maxcore'] = maxcore
        mconf[hostname]['minfreecore'] = minfreecore
        re = self.setMachineConf(mconf)
        print(("New machine conf: " + str(re)))
        return re

    def stop(self):
        self.fromClient.put("EXIT")

    def run(self):
        while True:
            if not self.fromClient.empty():
                msg = self.fromClient.get()
                print(("<ZmqClient> got message: " + str(msg)))
                if msg == "EXIT":
                    break
                else:
                    try:
                        print("<ZmqClient> sending to server...")
                        self.zmqsocket.send_pyobj(msg)
                        print("<ZmqClient> waiting for reply...")
                        response = self.zmqsocket.recv_pyobj()
                        self.toClient.put(response)
                    except zmq.ZMQError as e:
                        print(("<ZmqClient> Error occured: " + str(e)))
            time.sleep(0.1)
        self.zmqsocket.close()
        self.context.term()


def list_machines(client, args):
    machineconf = client.getMachineConf()
    pprint.pprint(machineconf)


def set_machines(client, args):
    try:
        machineconf = scheduler.parseMachineConf(args.machines)
        client.setMachineConf(machineconf)
    except ValueError as e:
        print(e)
        print(("machineconf was %s" % args.machines))
        machineconf = None
    print("new machine conf is:")
    list_machines(client, None)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Client for simple job scheduler")
    parser.add_argument('host', help="host running the server")
    parser.add_argument('-p',
                        '--port',
                        help="server port (default 8888)",
                        default=8888,
                        type=int)
    subparsers = parser.add_subparsers(help="subparsers help")

    parser_list = subparsers.add_parser('list', help='list current machines')
    parser_list.set_defaults(func=list_machines)

    parser_set = subparsers.add_parser('set', help='set machines')
    parser_set.add_argument(
        'machines',
        nargs='+',
        help=("format is " +
              "machineNr:maxcores:minfreecores (e.g. 2:6:1 9::16 8)." +
              "Both maxcores and minfreecores can be omitted, if so" +
              " maxcores is set to the number of cores of the " +
              " machine and minfreecores is set to zero."))
    parser_set.set_defaults(func=set_machines)

    #parser_change = subparsers.add_parser('change', help='change machine')
    args = parser.parse_args()

    #start client
    client = ZmqClient(host=args.host, port=args.port)
    client.start()

    #call selected command function
    args.func(client, args)
    client.stop()
