import csv
import os
import glob

#import BioKIT


def readResultFile(filehandle):
    """
    read results from a janus decoding in csv format
    
    Typically the file was created using the janus writeListOfArrays method 
    from the recognizer package. It must be a csv file with a semicolon used
    as delimiter and must contain a one-line header with the column names.
    
    Keyword arguments:
    filehandle -- filehandle of results file
    
    Returns a list of dictionaries with one dictionary for each decoding
    """
    csvDictReader = csv.DictReader(filehandle, delimiter=";")
    results = [x for x in csvDictReader]
    return results


def writeResultFile(filehandle, results):
    """write results of decoding in csv format to file"""
    assert len(results) > 0
    csvDictWriter = csv.DictWriter(filehandle,
                                   list(results[0].keys()),
                                   delimiter=";")
    csvDictWriter.writeheader()
    for res in results:
        csvDictWriter.writerow(res)


def readJanusConfig(filehandle):
    """
    read Janus rec.conf.tcl file and return a dictionary with the values
    """
    data = {}
    lines = filehandle.readlines()
    for line in lines:
        keyval = line.split(" ", 1)
        data[keyval[0]] = keyval[1]
    return data


def collectResults(baseDir):
    '''
    scan all subdirectories of baseDir for wer result files and return found results
    '''
    subDirs = [d for d in os.listdir(baseDir) if os.path.isdir(d)]
    results = {}
    for subdir in subDirs:
        werfiles = glob.glob(os.path.join(subdir, "wer*"))
        for werfile in werfiles:
            iteration = int(werfile[-1])
            with open(werfile, 'r') as f:
                wer = float(f.read().rstrip())

            print("found werfile for iteration: " + str(iteration) +
                  "with WER: " + str(wer))
            if iteration not in results:
                results[iteration] = {}
            results[iteration][subdir] = wer
    #compute average wer
    for iteration in results:
        avgwer = sum(results[iteration].values()) / len(
            list(results[iteration].values()))
        results[iteration]["avg"] = avgwer
    return results


def concatFoldResultStrings(baseDir, writeResultFile=True):
    print("test")
    subDirs = [
        os.path.join(baseDir, d) for d in os.listdir(baseDir)
        if os.path.isdir(os.path.join(baseDir, d))
    ]
    print(subDirs)
    results = {}
    #collect results
    for directory in subDirs:
        print(("descending into " + directory))
        resfiles = glob.glob(os.path.join(directory, "result.iter?"))
        print(resfiles)
        for resfile in resfiles:
            iteration = int(resfile[-1])
            if iteration not in results:
                results[iteration] = ""
            with open(resfile, "r") as f:
                foldres = f.read().rstrip()
                print(foldres)
                results[iteration] += " " + (foldres)
    #write out concatenated result files
    if writeResultFile:
        for iteration in list(results.keys()):
            with open(os.path.join(baseDir, "result.iter" + str(iteration)),
                      "w") as f:
                f.write(results[iteration] + "\n")
    return results


def writeSetFile(dataset, filename):
    '''
    Write a file containing the database ids given in dataset.
    
    arguments:
    dataset - a list of database ids
    filename - the target filename, can be a valid path or filename
    '''
    with open(filename, 'w') as f:
        f.write(" ".join([str(x) for x in dataset]))


def writeJoblist(jobs, directory, filename="joblist.tcl"):
    '''
    Write a list of jobs to execute via globalRunDist
    
    arguments:
    jobs - list of directory names with configured jobs in them
    directory - write joblist file into this directory
    filename - name of joblist file (default joblist.tcl)
    '''
    outString = ""
    outString += "set jobs {\n"
    for job in jobs:
        outString += "{ dirname \"" + job + "\" }\n"
    outString += "}\n"
    with open(os.path.join(directory, filename), "w") as f:
        f.write(outString)


def writeMachineList(machines, directory, filename="machines.tcl"):
    """
    Write a globalRunDistributed compatible list of machines to use
    
    arguments:
    machines: dictionary with host name and maximum number of cores to use
    directory: write machine list file into this directory
    filename: name of machine list file (default machines.tcl)
    """
    outString = ""
    outString += "set distribconf {\n"
    outString += " " * 4 + "machines {\n"
    for host, cores in machines.items():
        outString += " " * 8 + host + " {\n"
        outString += " " * 12 + "maxproc " + str(cores) + "\n"
        outString += " " * 8 + "}\n"
    outString += " " * 4 + "}\n"
    outString += "\n"
    outString += " " * 4 + "active {"
    for host in machines:
        outString += host + " "
    outString += "}\n"
    outString += "}"
    with open(os.path.join(directory, filename), "w") as f:
        f.write(outString)
