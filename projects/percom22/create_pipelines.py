from src.nodes.annotate_channel import Annotate_channel
from src.nodes.annotate_ui_button import Annotate_ui_button

from src.nodes.log_data import Log_data
from src.nodes.memory import Memory

from src.nodes.biokit_norm import Biokit_norm
from src.nodes.biokit_to_fs import Biokit_to_fs
from src.nodes.biokit_from_fs import Biokit_from_fs
from src.nodes.biokit_recognizer import Biokit_recognizer
from src.nodes.biokit_train import Biokit_train
from src.nodes.biokit_update_model import Biokit_update_model

from src.nodes.transform_scale import Transform_scale
from src.nodes.transform_feature import Transform_feature
from src.nodes.transform_window import Transform_window
from src.nodes.transform_filter import Transform_filter
from src.nodes.transform_majority_select import Transform_majority_select

from src.nodes.in_playback import In_playback
from src.nodes.in_data import In_data
from src.nodes.in_biosignalsplux import In_biosignalsplux
from src.nodes.in_riot import In_riot

from src.nodes.out_data import Out_data

from src.nodes.draw_lines import Draw_lines
from src.nodes.draw_recognition import Draw_recognition
from src.nodes.draw_search_graph import Draw_search_graph
from src.nodes.draw_gmm import Draw_gmm
from src.nodes.draw_text_display import Draw_text_display

from src.nodes.node import Node


def add_train(pl, norm):
    tokenDictionary = \
        { "cspin-ll": [ "cspin-ll_ISt", "cspin-ll_MSt", "cspin-ll_TSt", "cspin-ll_ISw", "cspin-ll_TSw"]
        , "cspin-lr": [ "cspin-lr_ISt", "cspin-lr_MSt", "cspin-lr_TSt", "cspin-lr_ISw", "cspin-lr_TSw"]

        , "cspin-rl": [ "cspin-rl_ISt", "cspin-rl_MSt", "cspin-rl_TSt", "cspin-rl_ISw", "cspin-rl_TSw"]
        , "cspin-rr": [ "cspin-rr_ISt", "cspin-rr_MSt", "cspin-rr_TSt", "cspin-rr_ISw", "cspin-rr_TSw"]
        , "cstep-l": [ "cstep-l_ISt", "cstep-l_MSt", "cstep-l_TSt", "cstep-l_ISw", "cstep-l_TSw"]

        , "cstep-r": [ "cstep-r_ISt", "cstep-r_MSt", "cstep-r_TSt", "cstep-r_ISw", "cstep-r_TSw"]
        , "jump-1": [ "jump-1_ITO", "jump-1_TTO", "jump-1_F", "jump-1_IL", "jump-1_TL"]

        , "jump-2": [ "jump-2_ITO", "jump-2_TTO", "jump-2_F", "jump-2_IL", "jump-2_TL"]

        , "run": [ "run_ISt", "run_MSt", "run_TSt", "run_ISw", "run_TSw"]

        , "shuffle-l": [ "shuffle-l_ISt", "shuffle-l_MSt", "shuffle-l_TSt", "shuffle-l_ISw", "shuffle-l_TSw"]
        , "shuffle-r": [ "shuffle-r_ISt", "shuffle-r_MSt", "shuffle-r_TSt", "shuffle-r_ISw", "shuffle-r_TSw"]

        , "sit": [ "sit_sitting" ]
        , "sit-stand": [ "sit-stand_sit2s" ]
        , "stair-down": [ "stair-down_ISt", "stair-down_MSt", "stair-down_TSt", "stair-down_ISw", "stair-down_TSw"]

        , "stair-up": [ "stair-up_ISt", "stair-up_MSt", "stair-up_TSt", "stair-up_ISw", "stair-up_TSw"]
        , "stand": [ "stand_standing" ]
        , "stand-sit": [ "stand-sit_stand2s"]

        , "vcut-ll": [ "vcut-ll_ISt", "vcut-ll_MSt", "vcut-ll_TSt", "vcut-ll_ISw", "vcut-ll_TSw"]
        , "vcut-lr": [ "vcut-lr_ISt", "vcut-lr_MSt", "vcut-lr_TSt", "vcut-lr_ISw", "vcut-lr_TSw"]

        , "vcut-rl": [ "vcut-rl_ISt", "vcut-rl_MSt", "vcut-rl_TSt", "vcut-rl_ISw", "vcut-rl_TSw"]
        , "vcut-rr": [ "vcut-rr_ISt", "vcut-rr_MSt", "vcut-rr_TSt", "vcut-rr_ISw", "vcut-rr_TSw"]
        , "walk": [ "walk_ISt", "walk_MSt", "walk_TSt", "walk_ISw", "walk_TSw"]
        }

    atomList = {val: list(map(str, range(1))) for atoms in tokenDictionary.values() for val in atoms}
    
        
    train = Biokit_train(model_path="./models/KneeBandageCSL2018/partition-stand/sequence/", \
        token_insertion_penalty=50,
        atomList=atomList,
        tokenDictionary=tokenDictionary,
        train_iterations=(5, 10)
        )
    train.add_input(norm)
    train.add_input(pl, emitting_channel="Termination", recv_data_stream='Termination')
    
    window1 = Transform_window(100, 0, name="File")
    select1 = Transform_majority_select(name="File")
    window1.add_input(pl, emitting_channel="File")
    select1.add_input(window1)
    train.add_input(select1, recv_data_stream='File')

    window2 = Transform_window(100, 0, name="Annotation")
    select2 = Transform_majority_select(name="Annotation")
    window2.add_input(pl, emitting_channel="Annotation")
    select2.add_input(window2)
    train.add_input(select2, recv_data_stream='Annotation')
    
    return train

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
    filter1 =Transform_filter(name="Annot Filter", names=["ACC_X", "ACC_Y", "ACC_Z", "GYRO_X", "GYRO_Y", "GYRO_Z"])
    filter1.add_input(pl)
    filter1.add_input(pl, emitting_channel="Channel Names", receiving_channel="Channel Names")

    to_fs = Biokit_to_fs()
    to_fs.add_input(filter1)

    norm = Biokit_norm()
    norm.add_input(to_fs)

    recog = Biokit_recognizer(model_path="./models/RIoT/sequence/", token_insertion_penalty=50)
    recog.add_input(norm)

    draw_recognition_path = Draw_recognition(xAxisLength=[x_raw, x_raw, x_raw, x_raw])
    draw_recognition_path.add_input(recog, emitting_channel="Recognition")
    draw_recognition_path.add_input(recog, data_stream='HMM Meta', recv_data_stream='HMM Meta')

    if has_annotation:
        memory = Memory(x_raw)
        memory.add_input(pl, data_stream='Annotation')
        draw_recognition_path.add_input(memory, recv_data_stream='Annotation')

    draw_search_graph = Draw_search_graph(n_hypos=1)
    draw_search_graph.add_input(recog, emitting_channel="HMM Meta", receiving_channel="HMM Meta")
    draw_search_graph.add_input(recog, emitting_channel="Hypothesis", receiving_channel="Hypothesis")

    draw_gmm = Draw_gmm(name="GMM X", plot_names=["ACC_X", "GYRO_X"], n_mixtures=1, n_scatter_points=15)
    draw_gmm.add_input(norm, emitting_channel="Data", receiving_channel="Data")
    draw_gmm.add_input(pl, emitting_channel="Channel Names", receiving_channel="Channel Names")
    draw_gmm.add_input(recog, emitting_channel="HMM Meta", receiving_channel="HMM Meta")
    draw_gmm.add_input(recog, emitting_channel="Hypo States", receiving_channel="Hypo States")

    draw_gmm = Draw_gmm(name="GMM Y", plot_names=["ACC_Y", "GYRO_Y"], n_mixtures=1, n_scatter_points=15)
    draw_gmm.add_input(norm, emitting_channel="Data", receiving_channel="Data")
    draw_gmm.add_input(pl, emitting_channel="Channel Names", receiving_channel="Channel Names")
    draw_gmm.add_input(recog, emitting_channel="HMM Meta", receiving_channel="HMM Meta")
    draw_gmm.add_input(recog, emitting_channel="Hypo States", receiving_channel="Hypo States")

    draw_gmm = Draw_gmm(name="GMM Z", plot_names=["ACC_Z", "GYRO_Z"], n_mixtures=1, n_scatter_points=15)
    draw_gmm.add_input(norm, emitting_channel="Data", receiving_channel="Data")
    draw_gmm.add_input(pl, emitting_channel="Channel Names", receiving_channel="Channel Names")
    draw_gmm.add_input(recog, emitting_channel="HMM Meta", receiving_channel="HMM Meta")
    draw_gmm.add_input(recog, emitting_channel="Hypo States", receiving_channel="Hypo States")

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
    x_raw = 1000
    x_processed = 10
    n_bits = 16

    print('=== Build RIoT Record Pipeline ===')
    pl = In_riot(id=0)
    # frm_ctr = Debug_frame_counter()
    # pl.add_input(frm_ctr)
    pl = add_riot_draw(pl, subset=0.5)
    save(pl, "riot_vis.json")

    annot = Annotate_ui_button(fall_back_target='None')
    annot.add_input(pl)

    out_data = Out_data(folder="./data/Debug/")
    out_data.add_input(annot)
    out_data.add_input(annot, emitting_channel="Annotation", receiving_channel="Annotation")
    out_data.add_input(pl, emitting_channel="Channel Names", receiving_channel="Channel Names")
    save(pl, "riot_record.json")


    print('=== Build RIoT Record and Update Pipeline ===')
    filter1 =Transform_filter(name="Annot Filter", names=["ACC_X", "ACC_Y", "ACC_Z", "GYRO_X", "GYRO_Y", "GYRO_Z"])
    filter1.add_input(annot)
    filter1.add_input(pl, emitting_channel="Channel Names", receiving_channel="Channel Names")

    to_fs = Biokit_to_fs()
    to_fs.add_input(filter1)

    norm = Biokit_norm()
    norm.add_input(to_fs)

    pl_train_new = Biokit_update_model(model_path="./models/RIoT/sequence", \
        token_insertion_penalty=20,
        phases_new_act=1,
        train_iterations=(7, 10),
        catch_all="None"
        )
    pl_train_new.add_input(norm)
    pl_train_new.add_input(annot, emitting_channel="Annotation", receiving_channel="Annotation")

    status_text = Draw_text_display(name="Training Status")
    status_text.add_input(pl_train_new, emitting_channel="Text", receiving_channel="Text")
    save(pl, "riot_record_update.json")
    


    print('=== Build RIoT Playback Pipeline ===')
    riot_meta = {
        "sample_rate": 100,
        "channels": In_riot.channels,
        "targets": ["None", "Right", "Left"]
    }

    pl = In_playback(files="./data/RIoT/*.h5", csv_columns=["start", "end", "act"], annotation_holes="", meta=riot_meta, batch=1)
    pl = add_riot_draw(pl, subset=0.5)
    save(pl, "riot_playback.json")


    print('=== Build RIoT Playback Recognition ===')
    pl = riot_add_recog(pl, has_annotation=True)
    save(pl, "riot_playback_recog.json")


    print('=== Build RIoT Live Recognition ===')
    pl = In_riot(id=0)
    pl = add_riot_draw(pl, subset=0.5)
    pl = riot_add_recog(pl, has_annotation=False)
    save(pl, "riot_live_recog.json")