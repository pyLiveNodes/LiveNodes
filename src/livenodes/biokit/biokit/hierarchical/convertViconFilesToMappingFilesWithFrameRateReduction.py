# -*- coding: utf8 -*-

import os
from string import *

# Main program
if __name__ == '__main__':

    folders = ['Broetchen', 'Kakao', 'Muesli', 'Orangensaft', 'Ruehrei']

    appendRBAK = False

    for folder in folders:
        for fileName in os.listdir(folder):
            fileName = os.path.join(folder, fileName)
            fileName2 = os.path.join('../../recordingsPoints/Felix', fileName)

            print("fileName " + str(fileName2))

            fileHandle = open(fileName)
            destFileHandle = open(fileName2, 'w')

            lines = [x for x in fileHandle]

            headerSize = 0
            #Skip header
            index = headerSize
            firstLine = True
            while index < len(lines):
                #Stop if reaching analog data
                if (count(lines[index], 'Sample') > 0):
                    break
                #Write only every tenth line
                if ((index - headerSize) % 10 == 0):
                    splittedLine = lines[index].split()
                    if (len(splittedLine) > 0):
                        #destFileHandle.write(splittedLine[0])
                        #for elementIndex in range(2,len(splittedLine)):
                        #	destFileHandle.write("	" + splittedLine[elementIndex])

                        for elementIndex in range(0, 25):
                            destFileHandle.write(splittedLine[elementIndex] +
                                                 "	")
                        if (appendRBAK == True):
                            if (firstLine == True):
                                destFileHandle.write("DUMMY:X	")
                                destFileHandle.write("DUMMY:Y    ")
                                destFileHandle.write("DUMMY:Z")
                                firstLine = False
                            else:
                                destFileHandle.write("0.000	")
                                destFileHandle.write("0.000     ")
                                destFileHandle.write("0.000")
                        for elementIndex in range(25, len(splittedLine)):
                            destFileHandle.write("	" +
                                                 splittedLine[elementIndex])
#destFileHandle.write(lines[index])
                        destFileHandle.write("\n")
                index += 1

            fileHandle.close()
            destFileHandle.close()

    print('Conversion finished')
