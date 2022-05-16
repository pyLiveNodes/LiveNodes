'''
Created on 06.03.2012

@author: camma
'''

import threading
import queue

import subprocess
import os
import sys
import socket
import time
import math
#import Database
#import airwritingConfig
import argparse
import zmq
from . import db
import sqlalchemy


class ExitSignal(Exception):
    """Exception indicating, that an EXIT signal was received"""
    pass


class Scheduler(threading.Thread):
    '''
    Simple job scheduler based on ssh remote execution
    '''

    def __init__(self, dbfile, command, directory, machines={}):
        '''
        Constructor
        '''
        threading.Thread.__init__(self, name="Scheduler")

        self.verbosity = 0
        self.dbfile = dbfile
        #self.db = db.AirDb(dbfile)
        self.machines = self.fillMachinesDict(machines)
        self.command = command
        if not os.path.isdir(directory):
            os.mkdir(directory)
        self.directory = directory

        #setup queue to receive control commands
        self._configInQueue = queue.Queue()
        self._configOutQueue = queue.Queue()

    def getConfigInQueue(self):
        return self._configInQueue

    def getConfigOutQueue(self):
        return self._configOutQueue

    def getNumberOfCores(self, hostname):
        """
        Get number of cores from target linux machine via ssh
        
        Keyword Arguments:
        hostname -- valid hostname of machine to check
        
        Returns number of cores or zero if an error in ssh execution occured
        """
        cmd = [
            "cat", "/proc/cpuinfo", "|", "grep", "processor", "|", "wc", "-l"
        ]
        retVal = self.remoteExec(hostname, cmd)
        if retVal:
            cores = int(retVal[:-1])
        else:
            cores = 0
        return cores

    def getLoad(self, hostname):
        """
        Get system load (1min average) of given host via ssh
        
        returns None if ssh remote execution didn't deliver a meaningful 
            load value
        """
        cmd = ['cat', '/proc/loadavg']
        loadstr = self.remoteExec(hostname, cmd)
        try:
            load1min = float(loadstr.split()[0])
        except:
            load1min = None
        finally:
            return load1min

    def startRemoteCommand(self, hostname, directory, logfile, command):
        """
        Execute the command in directory on remote host via ssh
        
        return pid of process or None if error occured
        """
        try:
            print("start job in " + directory + " on host " + hostname)
            cmd = ['ssh', '-f', hostname, 'cd', directory, ';']
            cmd.append(" ".join(command))
            cmd.extend(
                [' &> ',
                 os.path.join(directory, logfile), '&', 'echo', '$!'])
            pidstr = subprocess.check_output(cmd)
            return int(pidstr)
        except subprocess.CalledProcessError as err:
            print(("error, ssh returned " + str(err)))
            print(("command line was: " + " ".join(cmd)))
            return None

    def getIdleCores(self, hostname, offset=0.1):
        """get idle cores on host with respect to max cores set for the host"""
        cores = self.getNumberOfCores(hostname)
        load = self.getLoad(hostname)
        # print "cores " + str(cores) + " and load " + str(load)
        if cores != None and load != None:
            difference = (cores - load - offset)
            difference = int(math.floor(difference))
            if difference > 0:
                idle = difference
            else:
                idle = 0
        else:
            print(("Warning: cores " + str(cores) + " load " + str(load)))
            #problems with remote machine
            idle = None
        return idle

    def getNextJob(self):
        """get the next job with status waiting from the database"""
        job = self.db.session.query(db.Job).\
               filter(db.Job.status == "waiting").first()
        if job:
            job.status = "scheduling"
        self.db.session.commit()
        return job

    def getErrorJobs(self):
        """
        Get the jobs that finished with an error.
        :return: list of jobs with errors
        """
        errjobs = self.db.session.query(db.Job).\
            filter(db.Job.status == "error").all()
        return errjobs

    def runJob(self, hostname):
        """get job configuration from database and run it on remote machine"""
        job = self.getNextJob()
        retvalue = None
        if job:
            job.status = "running"
            t = time.localtime()
            timestr = str(t.tm_hour) + "_" + str(t.tm_min) + "_" + str(
                t.tm_sec)
            logfile = str(job.id) + "_" + timestr + ".log"
            cmd = [self.command, self.dbfile, str(job.id)]
            pid = self.startRemoteCommand(hostname, self.directory, logfile,
                                          cmd)
            retvalue = {'id': job.id, 'pid': pid, 'host': hostname}
        self.db.session.commit()
        return retvalue

    def isProcessFinished(self, hostname, pid):
        cmd = ['ps', '-p', str(pid)]
        ret = self.remoteExec(hostname, cmd)
        #print('isProcessFinished returned: ' + str(ret))
        if ret != None:
            return False
        else:
            return True

    def killProcess(self, hostname, pid):
        # find out session id
        cmd = ['ps', 'h', '-p', str(pid), '-o sid']
        sidstr = self.remoteExec(hostname, cmd)
        # kill complete session
        if sidstr:
            cmd = ['pkill', '-s', sidstr]
            self.remoteExec(hostname, cmd)

    def remoteExec(self, hostname, cmdlist):
        try:
            if self.verbosity > 0:
                print(("executing on " + hostname + ": " + " ".join(cmdlist)))
            cmd = ["ssh", hostname]
            cmd.extend(cmdlist)
            ret = subprocess.check_output(cmd)
            if self.verbosity > 0:
                print(("return value: " + str(ret)))
        except subprocess.CalledProcessError as err:
            print("error: " + str(err))
            ret = None
        return ret

    def fillMachinesDict(self, machines):
        '''
        Fill missing number of cores in given machine configuration.
        
        For any host given in the machine configuration is checked for validity.
        If None is given as number of cores to use, the number of cores of this
        machine is determined via remote access and inserted instead of None.
        
        A valid machine configuration is a dictionary with valid hostnames as
        keys and a integer number or None as value for each key. The number
        reflects the maximum number of jobs to start on the host.
        
        Keyword arguments:
        machines -- the variable to check
        
        Returns True if machines is a valid machine configuration and False
            otherwise
            
        Raises ValueError if number of jobs is not an integer
        Raises socket.gaierror if hostname is not a valid internet address
        '''
        for host, conf in list(machines.items()):
            socket.getaddrinfo(host, '22')
            if not conf['maxcore']:
                conf['maxcore'] = self.getNumberOfCores(host)
            if not conf['minfreecore']:
                conf['minfreecore'] = 0
            int(conf['maxcore'])
            int(conf['minfreecore'])
        return machines

    def _checkInQueue(self):
        """
        Handles messages in incoming queue.
        
        If command MACHINECONF is received, the machine conf is updated
        
        Raises ExitSignal if EXIT command was received
        """
        if not self._configInQueue.empty():
            msg = self._configInQueue.get()
            print(("received message: " + str(msg)))
            if msg['command'] == 'MACHINECONF':
                try:
                    self.machines = self.fillMachinesDict(msg['data'])
                    print(("received new machine configuration: " +
                           str(self.machines)))
                except (ValueError, socket.gaierror) as e:
                    print(("invalid machine configuration, error: " + str(e)))
                    pass
                finally:
                    self._configOutQueue.put(self.machines)
            elif msg['command'] == 'MACHINEINFO':
                self._configOutQueue.put(self.machines)
            elif msg['command'] == 'EXIT':
                print("received exit command, exiting...")
                raise ExitSignal()

    def reset_job_status(self, jobid, errstatus="error"):
        """
        reset the job status of erroneous finished jobs
        """
        self.db.session.commit(
        )  #make sure the current transaction is finished
        job = self.db.session.query(db.Job).filter(db.Job.id == jobid).one()
        if job.status != 'finished':
            print("job %s did not finish correctly, status is %s" %
                  (jobid, job.status))
            job.status = errstatus
            self.db.session.commit()

    def run(self):
        '''
        Starts the scheduling loop
           
        Waits for jobs in the the given job table and tries to find a machine
        to execute them. Runs until KeyboardInterrupt is encountered.
        
        All commands send via command queue must be dictionaries according to
        {'command': commandname, 'data': dataobject}
        
        The following commands are known
        MACHINECONF: data must contain a valid machine configuration, otherwise
            the command will be ignored.
        EXIT: Scheduler exits after terminating all running processes, data 
            field is ignored.
        '''
        self.runningJobs = []
        try:
            self.db = db.AirDb(self.dbfile)
            while True:

                print("check for finished jobs")
                finishedJobs = []
                for job in self.runningJobs:
                    if self.isProcessFinished(job['host'], job['pid']):
                        print(("Job %s on host %s finished" %
                               (job['pid'], job['host'])))
                        finishedJobs.append(job)
                        self.reset_job_status(job['id'])

                # delete finished jobs from runningJobs
                self.runningJobs = [
                    x for x in self.runningJobs if x not in finishedJobs
                ]
                print(("currently %s running jobs:" % len(self.runningJobs)))
                for j in self.runningJobs:
                    print(j)
                print(("%s jobs had errors" % len(self.getErrorJobs())))

                self._checkInQueue()

                print("check for idle cores and run new jobs")
                for host in self.machines:
                    idleCores = self.getIdleCores(host)
                    if idleCores != None:
                        availIdleCores = (idleCores -
                                          self.machines[host]['minfreecore'])
                        runningJobsHost = [
                            x for x in self.runningJobs if x['host'] == host
                        ]
                        running = len(runningJobsHost)
                        allowed = self.machines[host]['maxcore'] - running
                        freeslots = min(availIdleCores, allowed)
                        print(("host: " + host + "\t freeslots: " +
                               str(freeslots) + "\t idleCores: " +
                               str(idleCores) + "\t allowed: " + str(allowed) +
                               "\t availIdleCores: " + str(availIdleCores)))
                        if freeslots < 0:
                            freeslots = 0
                        for i in range(freeslots):
                            jobinfo = self.runJob(host)
                            if jobinfo:
                                self.runningJobs.append(jobinfo)
                                print("started job " + str(jobinfo))
                    else:
                        print(
                            "idleCores is None, there seems to be a problem!")
                #self.db.close()
                for i in range(30):
                    self._checkInQueue()
                    time.sleep(1)
        except ExitSignal:
            print("terminating running remote processes:")
            for job in self.runningJobs:
                print(("Killing process " + str(job['pid']) + " on " +
                       job['host']))
                self.killProcess(job['host'], job['pid'])
                self.reset_job_status(job['id'])
            print("exiting scheduler thread...")
            self._configOutQueue.put({'command': 'EXIT', 'data': None})


class ZmqServer(threading.Thread):

    def __init__(self, port, fromSchedQueue, toSchedQueue):
        threading.Thread.__init__(self, name='ZmqServer')
        self.fromSchedQueue = fromSchedQueue
        self.toSchedQueue = toSchedQueue

        self.msgqueue = queue.Queue()

        self.context = zmq.Context()
        self.zmqsocket = self.context.socket(zmq.REP)
        self.zmqsocket.bind('tcp://*:' + str(port))

    def run(self):
        while True:
            if not self.msgqueue.empty():
                msg = self.msgqueue.get()
                print(("received message: " + str(msg)))
                if msg == "EXIT":
                    break
            try:
                time.sleep(0.1)
                request = self.zmqsocket.recv_pyobj(zmq.NOBLOCK)
                self.toSchedQueue.put(request)
                answer = self.fromSchedQueue.get()
                self.zmqsocket.send_pyobj(answer)
            except zmq.ZMQError:
                pass
        self.zmqsocket.close()
        self.context.term()


def parseMachineConf(configList):
    """
    Parse list of machine configuration strings.
    
    Each list item must contain a valid machine config string according to
    hostnr|hostnr:[maxcore]|hostnr:[maxcore]:[minfreecore]
    
    Returns a dictionary of dictionaries with the hostname as primary key and 
    maxcore and minfreecore as secondary keys.
    """
    maxLen = 3
    machineInfo = {}
    for machinfo in configList:
        conf = machinfo.split(":")
        if len(conf) < 1 and len(conf) > maxLen:
            raise ValueError("%s is an invalid machine info" % machinfo)
        conf.extend(['' for x in range(maxLen - len(conf))])
        if int(conf[0]) not in list(range(255)):
            raise ValueError("%s is an invalid machine number" % conf[0])
        hostname = 'i19pc' + conf[0]
        if conf[1] != '':
            maxcore = int(conf[1])
        else:
            maxcore = None
        if conf[2] != '':
            minfreecore = int(conf[2])
        else:
            minfreecore = None
        machineInfo[hostname] = {
            'maxcore': maxcore,
            'minfreecore': minfreecore
        }
    return machineInfo


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple job scheduler")
    parser.add_argument('db', help="SQLAlchemy conform database url")
    parser.add_argument('command',
                        help="The command line to run, must " +
                        "accept <sqlite database> and <job id> as command " +
                        "line parameters. The command will be started as: " +
                        "command sqlitefile job_id")
    parser.add_argument('directory')
    parser.add_argument('-p',
                        '--port',
                        default=8888,
                        type=int,
                        help="port to listen on messages (default 8888)")
    parser.add_argument(
        'machines',
        nargs='+',
        help=("format is " +
              "machineNr:maxcores:minfreecores (e.g. 2:6:1 9::16 8)." +
              "Both maxcores and minfreecores can be omitted, if so" +
              " maxcores is set to the number of cores of the " +
              " machine and minfreecores is set to zero."))

    print(sys.argv)
    args = parser.parse_args()
    print(args)

    machineInfo = parseMachineConf(args.machines)

    scheduler = Scheduler(args.db, args.command, args.directory, machineInfo)
    scheduler.start()
    toSchedQueue = scheduler.getConfigInQueue()
    fromSchedQueue = scheduler.getConfigOutQueue()
    schedtimeout = 30.0

    server = ZmqServer(args.port, fromSchedQueue, toSchedQueue)
    serverQueue = server.msgqueue
    server.start()
    servertimeout = 5.0

    #loop until SIGINT is received or one of the threads died
    while scheduler.is_alive() and server.is_alive():
        try:
            time.sleep(0.1)
        except KeyboardInterrupt:
            print("Received SIGINT, exiting...")
            break

    if scheduler.is_alive():
        toSchedQueue.put({'command': 'EXIT', 'data': None})
    if server.is_alive():
        serverQueue.put("EXIT")
    print("Waiting for scheduler and server to shut down...")
    server.join(servertimeout)
    if server.is_alive():
        print(("Server thread didn't commit suicide in " + str(servertimeout) +
               "s, exit anyway..."))
    scheduler.join(schedtimeout)
    if scheduler.is_alive():
        print(("Scheduler thread didn't commit suicide in " +
               str(schedtimeout) + "s, exit anyway..."))
    print("Done, exit!")
    sys.exit()
