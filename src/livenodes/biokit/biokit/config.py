# -*- coding: UTF-8 -*-
__author__ = "Fabian Winnen, Jochen Weiner"

import ast

from . import BioKIT
from . import logger


class Config:
    """
    This class is a container for variable configurations which are read from a txt file.
    It can be used to get a better overview when changing single configurations in a bigger python script.
    See decoder/python/integration_test/_simple/IntegrationTestSpeechBN_TestParameters_parallel.py
    for a real world example
    You can find a short usage-example at the end of this file
    To execute the exampe below and see the output just type: "biokit config"

    config patterns: varname = value
    '#' indicate a comment
    spaces, tabs and newlines are ignored
    value can be any python expression including variables which were declared before

    you can only define variables which are listed 'config_variables'
    you must declare all those variables
    """

    def __init__(self, config_file_path, config_variables=[], verbose=True):
        """
        Initialize and Read configuration file

        Args:
            config_file_path - Path of the configuration path
            config_variables - (optional) Specify variables that have to be present in the file
            verbose - (optional) Print configuration values that have been read

        Raises:
            KeyError if a specified variable can not be found
        """
        self.__read_config(config_file_path, config_variables, verbose)

    def __read_config(self, config_file_path, config_variables, verbose):
        """ Read config file """
        with open(config_file_path) as config_file:
            logger.log(BioKIT.LogSeverityLevel.Information,
                       "Reading config file", config_file_path)

            for lineno, line in enumerate(config_file):
                line = line.strip()

                # filter empty lines, comments and lines with no definitions
                if line == "" or line.startswith('#') or '=' not in line:
                    continue

                # = divides key and value
                (key, val) = line.split('=')
                key = key.strip()
                val = val.strip()
                if key == '' or val == '':
                    raise ValueError(
                        "Syntax error in config file, line {}".format(
                            lineno + 1))  # lineno starts at 0

                # parse value to correct type and set key as class attribute
                val = ast.literal_eval(val)
                setattr(self, key, val)

                # log config
                if verbose:
                    logger.log(BioKIT.LogSeverityLevel.Information,
                               "   {:<30} = {}".format(key, repr(val)))

        # check if all specified config variables were found
        for variable in config_variables:
            if (variable not in self.__dict__):
                msg = "Variable '{}' is not set in config file {}".format(
                    variable, config_file_path)
                logger.log(BioKIT.LogSeverityLevel.Error, msg)
                raise KeyError(msg)

    def add(self, key, value):
        """
        Add a key-value-pair to the Config
        """
        setattr(self, key, value)

    def as_dict(self):
        """
        Return a dictionary representation of this config
        """
        return self.__dict__

    def __contains__(self, key):
        """
        Does this config have this key?
        """
        return hasattr(self, key)


################
# USAGE EXAMPLE
################

if __name__ == '__main__':
    print("Usage Example")

    # the txt-file where the config is declared
    # file pattern:
    # varname = value (which can be any valid python expression using the above variables)
    config_file_path = "config_example.txt"

    cnf = Config(config_file_path)

    # Access config
    print("var1 = " + str(cnf.var1) + str(type(cnf.var1)))
    print("var2 = " + str(cnf.var2) + str(type(cnf.var2)))
    print("var3 = " + str(cnf.var3) + str(type(cnf.var3)))
    print("var4 = " + str(cnf.var4) + str(type(cnf.var4)))
    print("var5 = " + str(cnf.var5) + str(type(cnf.var5)))
