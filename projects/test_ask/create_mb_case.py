from livenodes.plux.in_biosignalsplux import In_biosignalsplux
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

    global_registry.collect_modules(['livenodes.nodes', 'livenodes.plux'])

    # mapping from page 192: https://support.pluxbiosignals.com/wp-content/uploads/2021/11/OpenSignals_Manual.pdf
    channel_names = [ "EMG1"
        "ACC_X", "ACC_Y", "ACC_Z", 
        "MAG_X", "MAG_Y", "MAG_Z"]

    sample_rate = 400
    x_raw = sample_rate * 5 # gives us five seconds of data

    pl = In_biosignalsplux(adr="58:8E:81:A2:49:FC", freq=sample_rate, channel_names=channel_names, name="MuscleBan")
    
    draw_raw = Draw_lines(n_plots=len(channel_names), sample_rate=sample_rate, xAxisLength=x_raw, ylim=(-1, 2*16))
    draw_raw.connect_inputs_to(pl)
    
    save(pl, "MuscleBan_vis.json")

