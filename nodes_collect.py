from src.nodes.biokit_from_fs import Biokit_from_fs
from src.nodes.biokit_norm import Biokit_norm
from src.nodes.biokit_recognizer import Biokit_recognizer
from src.nodes.biokit_to_fs import Biokit_to_fs
from src.nodes.biokit_train import Biokit_train
from src.nodes.draw_lines import Draw_lines
from src.nodes.draw_recognition import Draw_recognition
from src.nodes.in_data import In_data
from src.nodes.in_playback import In_playback
from src.nodes.in_biosignalsplux import In_biosignalsplux
from src.nodes.memory import Memory
from src.nodes.node import Node
from src.nodes.out_data import Out_data
from src.nodes.receiver import Receiver
from src.nodes.transform_feature import Transform_feature
from src.nodes.transform_filter import Transform_filter
from src.nodes.transform_majority_select import Transform_majority_select
from src.nodes.transform_window import Transform_window
from src.nodes.transform_scale import Transform_scale
from src.nodes.transform_window_multiplier import Transform_window_multiplier

import json

# TODO: rather make this with auto detection and ignore filter and run automatically on main_qt startup...

if __name__ == "__main__":
    nodes = [Biokit_from_fs, 
    Biokit_norm, 
    Biokit_recognizer, 
    Biokit_to_fs, 
    Biokit_train, 
    Draw_lines, 
    Draw_recognition, 
    In_data, 
    In_playback, 
    In_biosignalsplux,
    Memory, 
    # Node, 
    Out_data, 
    # Receiver, 
    Transform_feature, 
    Transform_filter, 
    Transform_majority_select, 
    Transform_window, 
    Transform_scale,
    Transform_window_multiplier] 

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
        json.dump([node.info() for node in nodes], f, indent=2) 