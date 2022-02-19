from src.nodes.annotate_channel import Annotate_channel
from src.nodes.draw_search_graph import Draw_search_graph
from src.nodes.transform_scale import Transform_scale
from src.nodes.log_data import Log_data
from src.nodes.in_biosignalsplux import In_biosignalsplux
from src.nodes.in_riot import In_riot
from src.nodes.biokit_norm import Biokit_norm
from src.nodes.biokit_to_fs import Biokit_to_fs
from src.nodes.biokit_from_fs import Biokit_from_fs
from src.nodes.biokit_recognizer import Biokit_recognizer
from src.nodes.biokit_train import Biokit_train

from src.nodes.transform_feature import Transform_feature
from src.nodes.transform_window import Transform_window
from src.nodes.transform_filter import Transform_filter
from src.nodes.transform_majority_select import Transform_majority_select

from src.nodes.memory import Memory
from src.nodes.in_playback import In_playback
from src.nodes.in_data import In_data
from src.nodes.out_data import Out_data

from src.nodes.draw_lines import Draw_lines
from src.nodes.draw_recognition import Draw_recognition

from src.nodes.debug_frame_counter import Debug_frame_counter

from src.nodes.node import Node



def add_processing(pl_in, x_raw, x_processed, vis=(True, True, True)):
    # This output will not be saved, as it cannot be reconstructed
    pl_in.add_output(lambda data: print(data))

    if vis[0]:
        filter1 =Transform_filter(name="Raw Filter", names=channel_names_raw)
        pl_in.add_output(filter1)
        pl_in.add_output(filter1, data_stream="Channel Names", recv_data_stream="Channel Names")

        draw_raw = Draw_lines(name='Raw Data', n_plots=len(channel_names_raw), xAxisLength=x_raw)
        filter1.add_output(draw_raw)
        filter1.add_output(draw_raw, data_stream="Channel Names", recv_data_stream="Channel Names")

    window = Transform_window(100, 0)
    pl_in.add_output(window)

    fts = Transform_feature(features=['calc_mean', 'rms'], feature_args={"samplingfrequency": meta['sample_rate']})
    window.add_output(fts)
    pl_in.add_output(fts, data_stream="Channel Names", recv_data_stream="Channel Names")

    if vis[1]:
        filter2 =Transform_filter(name="Feature Filter", names=channel_names_fts)
        fts.add_output(filter2)
        fts.add_output(filter2, data_stream="Channel Names", recv_data_stream="Channel Names")

        draw_fts = Draw_lines(name='Features', n_plots=len(channel_names_fts), xAxisLength=x_processed)
        filter2.add_output(draw_fts)
        filter2.add_output(draw_fts, data_stream="Channel Names", recv_data_stream="Channel Names")

    to_fs = Biokit_to_fs()
    fts.add_output(to_fs)

    norm = Biokit_norm()
    to_fs.add_output(norm)

    if vis[2]:
        from_fs = Biokit_from_fs()
        norm.add_output(from_fs)

        filter3 =Transform_filter(name="Normed Feature Filter", names=channel_names_fts)
        from_fs.add_output(filter3)
        fts.add_output(filter3, data_stream="Channel Names", recv_data_stream="Channel Names")

        draw_normed = Draw_lines(name='Normed Features', n_plots=len(channel_names_fts), ylim=(-5, 5), xAxisLength=x_processed)
        filter3.add_output(draw_normed)
        filter3.add_output(draw_normed, data_stream="Channel Names", recv_data_stream="Channel Names")

    return norm


def add_recognition(pl, norm, x_raw, x_processed, vis=True):
    window1 = Transform_window(100, 0, name="File")
    select1 = Transform_majority_select(name="File")
    pl.add_output(window1, data_stream="File")
    window1.add_output(select1)

    recog = Biokit_recognizer(model_path="./models/KneeBandageCSL2018/partition-stand/sequence/", token_insertion_penalty=50)
    norm.add_output(recog)
    select1.add_output(recog, recv_data_stream="File")

    if vis:
        draw_recognition_path = Draw_recognition(xAxisLength=[x_processed, x_processed, x_processed, x_raw])
        recog.add_output(draw_recognition_path, data_stream="Recognition")
        recog.add_output(draw_recognition_path, data_stream='HMM Meta', recv_data_stream='HMM Meta')

        memory = Memory(x_raw)
        pl.add_output(memory, data_stream='Annotation')
        memory.add_output(draw_recognition_path, recv_data_stream='Annotation')

    if vis:
        draw_search_graph = Draw_search_graph()
        recog.add_output(draw_search_graph, data_stream="HMM Meta", recv_data_stream="HMM Meta")
        recog.add_output(draw_search_graph, data_stream="Hypothesis", recv_data_stream="Hypothesis")

    return recog


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
    norm.add_output(train)
    pl.add_output(train, data_stream="Termination", recv_data_stream='Termination')
    
    window1 = Transform_window(100, 0, name="File")
    select1 = Transform_majority_select(name="File")
    pl.add_output(window1, data_stream="File")
    window1.add_output(select1)
    select1.add_output(train, recv_data_stream='File')

    window2 = Transform_window(100, 0, name="Annotation")
    select2 = Transform_majority_select(name="Annotation")
    pl.add_output(window2, data_stream="Annotation")
    window2.add_output(select2)
    select2.add_output(train, recv_data_stream='Annotation')
    
    return train

def add_riot_draw(pl, subset=2):
    if subset == 0:
        f = ["ACC_X", "ACC_Y", "ACC_Z"]
    elif subset == 1:
        f = ["ACC_X", "ACC_Y", "ACC_Z", "GYRO_X", "GYRO_Y", "GYRO_Z", "MAG_X", "MAG_Y", "MAG_Z"]
    elif subset == 2:
        f = ["A1", "A2", "C", "Q1", "Q2", "Q3", "Q4", "PITCH", "YAW", "ROLL", "HEAD"]
    else:
        f = ["ACC_X", "ACC_Y", "ACC_Z", "GYRO_X", "GYRO_Y", "GYRO_Z", "MAG_X", "MAG_Y", "MAG_Z","TEMP", "IO", "A1", "A2", "C", "Q1", "Q2", "Q3", "Q4", "PITCH", "YAW", "ROLL", "HEAD"]

    filter1 =Transform_filter(name="Raw Filter", names=f)
    pl.add_output(filter1)
    pl.add_output(filter1, data_stream="Channel Names", recv_data_stream="Channel Names")

    draw_raw = Draw_lines(name='Raw Data', n_plots=len(f), sample_rate=100, xAxisLength=x_raw)
    filter1.add_output(draw_raw)
    filter1.add_output(draw_raw, data_stream="Channel Names", recv_data_stream="Channel Names")

    return pl

# From: https://stackoverflow.com/questions/2556108/rreplace-how-to-replace-the-last-occurrence-of-an-expression-in-a-string
def rreplace(s, old, new, occurrence):
  li = s.rsplit(old, occurrence)
  return new.join(li)

def save(pl, file):
    print('--- Save Pipeline ---')
    pl.save(file)


    print('--- Load Pipeline ---')
    pl_val = Node.load(file)

    # TODO: validate & test pipeline
    # print()

    print('--- Visualize Pipeline ---')
    pl_val.make_dot_graph(transparent_bg=True).save(rreplace(file, '/', '/gui/', 1).replace('.json', '.png'), 'PNG')
    pl_val.make_dot_graph(transparent_bg=False).save(file.replace('.json', '.png'), 'PNG')


if __name__ == "__main__":
    channel_names_raw = ['EMG1', 'Gonio2', 'AccLow2']
    # channel_names_fts = ['EMG1__calc_mean', 'Gonio2__calc_mean', 'AccLow2__calc_mean']
    channel_names_fts = ['EMG1__rms', 'Gonio2__calc_mean', 'AccLow2__calc_mean']
    recorded_channels = [
        'EMG1', 'EMG2', 'EMG3', 'EMG4',
        'Airborne',
        'AccUp1', 'AccUp2', 'AccUp3',
        'Gonio1',
        'AccLow1', 'AccLow2', 'AccLow3',
        'Gonio2',
        'GyroUp1', 'GyroUp2', 'GyroUp3',
        'GyroLow1', 'GyroLow2', 'GyroLow3']

    meta = {
        "sample_rate": 1000,
        "channels": recorded_channels,
        "targets": ['cspin-ll', 'run', 'jump-2', 'shuffle-l', 'sit', 'cstep-r', 'vcut-rr', 'stair-down', 'stand-sit', 'jump-1', 'sit-stand', 'stand', 'cspin-lr', 'cspin-rr', 'cstep-l', 'vcut-ll', 'vcut-rl', 'shuffle-r', 'stair-up', 'walk', 'cspin-rl', 'vcut-lr']
    }

    # x_raw = 10000
    # x_processed = 100

    x_raw = 5000
    x_processed = 50
    n_bits = 16

    print('=== Build Live Connection Pipeline ===')
    pl = In_biosignalsplux("00:07:80:B3:83:ED", 1000, n_bits=n_bits, channel_names=["Pushbutton"])
    # pl.add_output(Log_data())
    scaler = Transform_scale(0, 2**n_bits)
    pl.add_output(scaler)
    draw_raw = Draw_lines(name='Raw Data', n_plots=1, xAxisLength=x_raw)
    scaler.add_output(draw_raw)
    pl.add_output(draw_raw, data_stream="Channel Names", recv_data_stream="Channel Names")
    annotate_channel = Annotate_channel("Pushbutton", [1, -1])
    pl.add_output(annotate_channel, data_stream="Channel Names", recv_data_stream="Channel Names")
    scaler.add_output(annotate_channel)
    draw_raw2 = Draw_lines(name='Annotation', n_plots=1, xAxisLength=x_raw)
    annotate_channel.add_output(draw_raw2, data_stream="Annotation")
    save(pl, "pipelines/process_live.json")


    print('=== Build Processing Pipeline ===')
    # TODO: currently the saving and everything else assumes we have a single node as entry, not sure if that is always true. consider multi indepdendent sensors, that are synced in the second node 
    #   -> might be solveable with "pipeline nodes" or similar, where a node acts as container for a node system -> might be good for paralellisation anyway 
    pl = In_playback(files="./data/KneeBandageCSL2018/part00/01.h5", meta=meta, batch=20)
    # pl = Playback(files="./data/KneeBandageCSL2018/**/*.h5", meta=meta, batch=20)

    norm = add_processing(pl, x_raw=x_raw, x_processed=x_processed, vis=(True, True, True))
    save(pl, "pipelines/preprocess.json")


    print('=== Build Recognition Pipeline ===')
    pl = In_playback(files="./data/KneeBandageCSL2018/part00/01.h5", meta=meta, batch=20)
    norm = add_processing(pl, x_raw=x_raw, x_processed=x_processed, vis=(False, False, True))
    recog = add_recognition(pl, norm, x_raw=x_raw, x_processed=x_processed, vis=True)
    save(pl, "pipelines/recognize.json")


    print('=== Build Recognition Pipeline (no vis) ===')
    pl = In_data(files="./data/KneeBandageCSL2018/part00/*.h5", meta=meta, batch=2000)
    norm = add_processing(pl, x_raw=x_raw, x_processed=x_processed, vis=(False, False, False))
    recog = add_recognition(pl, norm, x_raw=x_raw, x_processed=x_processed, vis=False)
    save(pl, "pipelines/recognize_no_vis.json")


    print('=== Build Train Pipeline ===')

    pl = In_data(files="./data/KneeBandageCSL2018/part*/*.h5", meta=meta, batch=2000)
    norm = add_processing(pl, x_raw=x_raw, x_processed=x_processed, vis=(False, False, False))
    save(pl, "pipelines/preprocess_no_vis.json")

    train = add_train(pl, norm)
    save(pl, "pipelines/train.json")





    x_raw = 1000
    x_processed = 10
    n_bits = 16

    print('=== Build RIoT Record Pipeline ===')
    pl = In_riot(id=0)
    # frm_ctr = Debug_frame_counter()
    # pl.add_output(frm_ctr)
    pl = add_riot_draw(pl)
    save(pl, "pipelines/riot_vis.json")

    out_data = Out_data(folder="./data/Debug/")
    pl.add_output(out_data)
    pl.add_output(out_data, data_stream="Channel Names", recv_data_stream="Channel Names")
    save(pl, "pipelines/riot_record.json")


    print('=== Build RIoT Playback Pipeline ===')
    riot_meta = {
        "sample_rate": 100,
        "channels": In_riot.channels,
        "targets": []
    }

    pl = In_playback(files="./data/RIoT/*.h5", meta=riot_meta, batch=1)
    pl = add_riot_draw(pl)
    save(pl, "pipelines/riot_playback.json")