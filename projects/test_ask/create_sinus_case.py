from livenodes.nodes.in_function import In_function
from livenodes.nodes.transform_filter import Transform_filter
from livenodes.nodes.draw_lines import Draw_lines

from livenodes.core.node import Node
from livenodes.core import global_registry

def save(pl, file):
    print('--- Save Pipeline ---')
    pl.save(f"pipelines/{file}")


    print('--- Load Pipeline ---')
    pl_val = Node.load(f"pipelines/{file}")

    # TODO: validate & test pipeline
    # print()

    print('--- Visualize Pipeline ---')
    vis = file.replace('.json', '.png')
    pl_val.dot_graph_full(transparent_bg=True).save(f"gui/{vis}", 'PNG')
    pl_val.dot_graph_full(transparent_bg=False).save(f"pipelines/{vis}", 'PNG')


if __name__ == "__main__":
    import os 
    log_folder = './logs/'
    gui_folder = './gui/'

    if not os.path.exists(log_folder):
        os.mkdir(log_folder)

    if not os.path.exists(gui_folder):
        os.mkdir(gui_folder)

    global_registry.collect_modules(['livenodes.nodes'])


    channel_names_raw = ['Sinus', 'Linear']
    recorded_channels = ['Sinus', 'Linear']

    meta = {
        "sample_rate": 10,
        "channels": recorded_channels,
        "targets": ['cspin-ll', 'run', 'jump-2', 'shuffle-l', 'sit', 'cstep-r', 'vcut-rr', 'stair-down', 'stand-sit', 'jump-1', 'sit-stand', 'stand', 'cspin-lr', 'cspin-rr', 'cstep-l', 'vcut-ll', 'vcut-rl', 'shuffle-r', 'stair-up', 'walk', 'cspin-rl', 'vcut-lr']
    }

    x_raw = 50

    pl = In_function(meta=meta, function="linear", emit_at_once=1)
    
    filter1 = Transform_filter(channel_names_raw)
    filter1.connect_inputs_to(pl)

    draw_raw = Draw_lines(n_plots=len(channel_names_raw), sample_rate=meta['sample_rate'], xAxisLength=x_raw)
    draw_raw.connect_inputs_to(filter1)
    
    save(pl, "sinus.json")

