import json 
from functools import reduce
import os

class State():
    def __init__(self, values={}):
        self.__spaces = {}
        self.__values = values

    def space_create(self, name, values={}):
        if name in self.__spaces:
            raise ValueError('Space already exists')
        self.__spaces[name] = State(values=values)
        return self.__spaces[name]
    
    def space_add(self, name, state):
        if name in self.__spaces:
            raise ValueError('Space already exists')
        self.__spaces[name] = state

    def space_get(self, name, fallback={}):
        if name not in self.__spaces:
            return self.space_create(name, values=fallback)
        return self.__spaces.get(name)

    def __repr__(self):
        return '{values: ' + ','.join(self.__values.keys()) + 'spaces: ' + ','.join(self.__spaces.keys()) + '}'

    def val_merge(self, *args):
        # merges all dicts that are passed as arguments into the current values
        # later dicts overwrite earlier ones
        # self.__values is maintained
        self.__values = reduce(lambda cur, nxt: {**nxt, **cur}, reversed([*args, self.__values]), {})

    def val_exists(self, key):
        return key in self.__values

    def val_get(self, key, fallback=None):
        if key not in self.__values and fallback is not None:
            self.__values[key] = fallback
        return self.__values[key]

    def val_set(self, key, val):
        self.__values[key] = val

    def dict_to(self):
        return {
            'spaces': {key: val.dict_to() for key, val in self.__spaces.items()},
            'values': self.__values
        }

    @staticmethod
    def dict_from(dct):
        state = State(dct.get('values', {}))
        for key, space in dct.get('spaces', {}).items():
            state.space_add(key, State.dict_from(space))
        return state

    def save(self, path):
        with open(path, 'w') as f:
            json.dump(self.dict_to(), f, indent=2)

    @staticmethod
    def load(path):
        if os.path.exists(path):
            with open(path, 'r') as f:
                space = json.load(f)
                return State.dict_from(space)
        return State({})