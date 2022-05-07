# -*- coding: utf-8 -*-

import argparse
import re
import subprocess
import sys

"""
Parse a BioKIT log file with a stack trace.
Read functions, file names and line numbers of the addresses from the executable
and produce a more human-readable stack trace
"""


def __get_functions_and_lines(addresses):
    """
    Get the function names, files and line numbers for given addresses.
    Uses the binutils program "addr2line".

    Args:
        addresses - list of addresses (0x...)

    Returns:
        list of tuples (function name, file:lineNo)
    """
    # get line number
    output = subprocess.check_output(["addr2line",
                                      "-Cf",
                                      "-e", sys.executable]
                                     + addresses,
                                     universal_newlines=True)
    output = output.split("\n")

    # merge names and lines
    output_merged = []
    for i in range(len(addresses)):
        # return address if no line number was found
        if output[2*i+1] == "??:0":
            output[2*i+1] = "[{}]".format(addresses[i])
        # merge
        output_merged.append((output[2*i], output[2*i+1]))

    return output_merged


def __get_line(address):
    """
    Get the file and line number for given address.
    Uses the binutils program "addr2line".
    """
    # get line number
    output = subprocess.check_output(["addr2line",
                                      "-e", sys.executable,
                                      address])
    output = output.strip()

    # return address if no line number was found
    if output == "??:0":
        output = "[{}]".format(address)

    return output.strip()


def parse(log_path):
    """
    Parse the backtrace in the log file and print enriched back trace output
    """
    signal_expr = re.compile("signal [0-9]{1,2} \(.*?\), address is .*? from ")
    trace_expr = re.compile("(?P<begin> \([0-9]+\) [^() ]*)( : |\(\) )(?P<middle>.*?)\[(?P<address>0x[0-9a-f]+)\]")

    first_line = ""
    trace_line_begins = []
    trace_line_functions = []
    trace_line_addresses = []

    # read log file
    with open(log_path) as log_file:
        for line in log_file:
            line = line.rstrip()

            # head line
            if not first_line and re.match(signal_expr, line):
                first_line = line

            # trace lines
            elif first_line:
                match = re.match(trace_expr, line)
                if match:
                    trace_line_begins.append(match.group('begin'))
                    trace_line_functions.append(match.group('middle'))
                    trace_line_addresses.append(match.group('address'))

    # get lines
    trace_line_addresses = __get_functions_and_lines(trace_line_addresses)

    # print output
    print(first_line)
    print("backtrace:")
    for begin, functionOrg, (function, lineNo) in zip(trace_line_begins, trace_line_functions, trace_line_addresses):
        if function == "??" and functionOrg != "":
            function = functionOrg

        print("{} : {} {}".format(begin, function, lineNo))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse log file with a BioKIT stack trace. Run this script with the same BioKIT version that created the log file")
    parser.add_argument("log", help="log file that includes the stack trace")
    args = parser.parse_args()

    parse(args.log)
