import glob 
import importlib
import json
import traceback

def discover_nodes():
    ignore = ['utils', 'node', '__init__', 'draw_gmm']
    files = [f.replace('/', '.').replace('.py', '') for f in list(glob.glob("src/nodes/*.py"))]
    imports = [(f, f.split('.')[-1].capitalize()) for f in files if f.split('.')[-1] not in ignore]
    return imports

def discover_infos():
    nodes = discover_nodes()
   
    info = []
    for pth, cls_name in nodes:
        try:
            module = importlib.import_module(pth)
            cls = getattr(module, cls_name)
            info.append(cls.info())    
        except Exception as err:
            print(f'Could not load {cls_name} from {pth}')
            print(err)
            print(traceback.format_exc())
    
    return info

# TODO: rather make this with auto detection and ignore filter and run automatically on main_qt startup...

if __name__ == "__main__":
    # Creates a json file with all available nodes
    # This is used in two cases:
    # (1) all necessary information for the gui to create and edit pipelines
    # (2) [currently not implemented] a cleaner way of importing classes rather than having the class_name.py -> Class_name scheme
    # 
    # The information for each node added should be:
    # - Class Name
    # - (File name)?
    # - in streams 
    # - out streams
    # - init parameters
    # TODO: anything else?
    
    with open("nodes.json", 'w') as f:
        json.dump(discover_infos(), f, indent=2) 