from livenodes.nodes.memory import Memory

from livenodes.biokit.biokit_norm import Biokit_norm
from livenodes.biokit.biokit_to_fs import Biokit_to_fs
from livenodes.biokit.biokit_from_fs import Biokit_from_fs
from livenodes.biokit.biokit_recognizer import Biokit_recognizer
from livenodes.biokit.biokit_train import Biokit_train
from livenodes.biokit.biokit_update_model import Biokit_update_model

from livenodes.nodes.transform_feature import Transform_feature
from livenodes.nodes.transform_window import Transform_window
from livenodes.nodes.transform_filter import Transform_filter
from livenodes.nodes.annotate_ui_button import Annotate_ui_button
from livenodes.nodes.transform_majority_select import Transform_majority_select

from livenodes.nodes.in_playback import In_playback
from livenodes.plux.in_riot import In_riot

from livenodes.nodes.out_data import Out_data

from livenodes.nodes.draw_lines import Draw_lines
from livenodes.nodes.draw_recognition import Draw_recognition
from livenodes.nodes.draw_search_graph import Draw_search_graph
from livenodes.nodes.draw_gmm import Draw_gmm
from livenodes.nodes.draw_text_display import Draw_text_display

from livenodes.core.node import Node
from livenodes.core import global_registry

def add_riot_draw(pl, subset=2):
    if subset == 0:
        f = ["ACC_X", "ACC_Y", "ACC_Z"]
    elif subset == 0.5:
        f = ["ACC_X", "ACC_Y", "ACC_Z", "GYRO_X", "GYRO_Y", "GYRO_Z"]
    elif subset == 1:
        f = ["ACC_X", "ACC_Y", "ACC_Z", "GYRO_X", "GYRO_Y", "GYRO_Z", "MAG_X", "MAG_Y", "MAG_Z"]
    elif subset == 2:
        f = ["A1", "A2", "C", "Q1", "Q2", "Q3", "Q4", "PITCH", "YAW", "ROLL", "HEAD"]
    else:
        f = ["ACC_X", "ACC_Y", "ACC_Z", "GYRO_X", "GYRO_Y", "GYRO_Z", "MAG_X", "MAG_Y", "MAG_Z","TEMP", "IO", "A1", "A2", "C", "Q1", "Q2", "Q3", "Q4", "PITCH", "YAW", "ROLL", "HEAD"]

    filter1 =Transform_filter(name="Raw Filter", names=f)
    filter1.add_input(pl)
    filter1.add_input(pl, emitting_channel="Channel Names", receiving_channel="Channel Names")

    draw_raw = Draw_lines(name='Raw Data', n_plots=len(f), sample_rate=100, xAxisLength=x_raw)
    draw_raw.add_input(filter1)
    draw_raw.add_input(filter1, emitting_channel="Channel Names", receiving_channel="Channel Names")

    return pl

def riot_add_recog(pl, has_annotation=False):
    filter1 = Transform_filter(name="Annot Filter", names=["ACC_X", "ACC_Y", "ACC_Z", "GYRO_X", "GYRO_Y", "GYRO_Z"])
    filter1.add_input(pl)
    filter1.add_input(pl, emitting_channel="Channel Names", receiving_channel="Channel Names")

    to_fs = Biokit_to_fs()
    to_fs.add_input(filter1)

    recog = Biokit_recognizer(model_path="./models/RIoT/sequence/", token_insertion_penalty=50)
    recog.add_input(to_fs)
    if "File" in pl.channels_out:
        recog.add_input(pl, emitting_channel="File", receiving_channel="File")

    draw_recognition_path = Draw_recognition(xAxisLength=[x_raw, x_raw, x_raw, x_raw])
    draw_recognition_path.connect_inputs_to(recog)

    if has_annotation:
        memory = Memory(x_raw)
        memory.add_input(pl, emitting_channel='Annotation')
        draw_recognition_path.add_input(memory, receiving_channel='Annotation')

    draw_search_graph = Draw_search_graph(n_hypos=1)
    draw_search_graph.connect_inputs_to(recog)

    draw_gmm = Draw_gmm(name="GMM X", plot_names=["ACC_X", "GYRO_X"], n_mixtures=1, n_scatter_points=15)
    draw_gmm.connect_inputs_to(filter1)
    draw_gmm.connect_inputs_to(recog)

    draw_gmm = Draw_gmm(name="GMM Y", plot_names=["ACC_Y", "GYRO_Y"], n_mixtures=1, n_scatter_points=15)
    draw_gmm.connect_inputs_to(filter1)
    draw_gmm.connect_inputs_to(recog)

    draw_gmm = Draw_gmm(name="GMM Z", plot_names=["ACC_Z", "GYRO_Z"], n_mixtures=1, n_scatter_points=15)
    draw_gmm.connect_inputs_to(filter1)
    draw_gmm.connect_inputs_to(recog)

    return pl

# From: https://stackoverflow.com/questions/2556108/rreplace-how-to-replace-the-last-occurrence-of-an-expression-in-a-string
def rreplace(s, old, new, occurrence):
  li = s.rsplit(old, occurrence)
  return new.join(li)

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

    global_registry.collect_modules(['livenodes.nodes', 'livenodes.biokit', 'livenodes.plux'])

    x_raw = 1000
    x_processed = 10
    n_bits = 16

    # === Online stuff ========================================================

    print('=== Build RIoT Record Pipeline ===')
    pl = In_riot(id=0, listen_port=9000)
    # frm_ctr = Debug_frame_counter()
    # pl.add_input(frm_ctr)
    pl = add_riot_draw(pl, subset=0.5)
    save(pl, "live_vis.json")

    annot = Annotate_ui_button(fall_back_target='None')
    annot.add_input(pl)

    out_data = Out_data(folder="./data/Debug/")
    out_data.add_input(annot)
    out_data.add_input(annot, emitting_channel="Annotation", receiving_channel="Annotation")
    out_data.add_input(pl, emitting_channel="Channel Names", receiving_channel="Channel Names")
    save(pl, "live_record.json")


    print('=== Build RIoT Record and Update Pipeline ===')
    filter1 = Transform_filter(name="Annot Filter", names=["ACC_X", "ACC_Y", "ACC_Z", "GYRO_X", "GYRO_Y", "GYRO_Z"])
    filter1.add_input(annot)
    filter1.add_input(pl, emitting_channel="Channel Names", receiving_channel="Channel Names")

    to_fs = Biokit_to_fs()
    to_fs.add_input(filter1)

    # norm = Biokit_norm()
    # norm.add_input(to_fs)

    pl_train_new = Biokit_update_model(model_path="./models/RIoT/sequence", \
        token_insertion_penalty=20,
        phases_new_act=1,
        train_iterations=(7, 10),
        catch_all="None"
        )
    pl_train_new.add_input(to_fs)
    pl_train_new.add_input(annot, emitting_channel="Annotation", receiving_channel="Annotation")

    status_text = Draw_text_display(name="Training Status")
    status_text.add_input(pl_train_new, emitting_channel="Text", receiving_channel="Text")
    save(pl, "live_record_update.json")
    

    print('=== Build RIoT Live Recognition ===')
    pl = In_riot(id=0)
    pl = add_riot_draw(pl, subset=0.5)
    pl = riot_add_recog(pl, has_annotation=False)
    save(pl, "live_recog.json")


    # === Offline stuff ========================================================


    print('=== Build RIoT Playback Pipeline ===')
    riot_meta = {
        "sample_rate": 100,
        "channels": In_riot.channels,
        "targets": ["None", "Right", "Left"]
    }

    pl = In_playback(files="./data/RIoT/*.h5", csv_columns=["start", "end", "act"], annotation_holes="None", meta=riot_meta, emit_at_once=1)
    pl = add_riot_draw(pl, subset=0.5)
    save(pl, "playback_vis.json")


    print('=== Build RIoT Playback Recognition ===')
    pl = riot_add_recog(pl, has_annotation=True)
    save(pl, "playback_recog.json")


    