def convertDictToJanus(dictionary):
    outputString = ""
    for key, val in dictionary.items():
        outputString += "{"
        outputString += key
        outputString += " {" + str(val) + "}} "
    return (outputString)


def writeJanusArraysToFile(entries, filename):
    with open(filename, 'w') as f:
        for ent in entries:
            f.write("{")
            f.write(ent)
            f.write("} ")
