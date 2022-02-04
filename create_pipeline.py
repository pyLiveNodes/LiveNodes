from src.nodes.biokit_norm import Biokit_norm
from src.nodes.biokit_to_fs import Biokit_to_fs
from src.nodes.biokit_from_fs import Biokit_from_fs
from src.nodes.biokit_recognizer import Biokit_recognizer

from src.nodes.transform_feature import Transform_feature
from src.nodes.transform_window import Transform_window
from src.nodes.transform_filter import Transform_filter

from src.nodes.memory import Memory
from src.nodes.in_playback import In_playback
from src.nodes.in_data import In_data

from src.nodes.draw_lines import Draw_lines
from src.nodes.draw_recognition import Draw_recognition

from src.nodes.node import Node



def add_processing(pl_in, x_raw, x_processed, vis=True):
    # This output will not be saved, as it cannot be reconstructed
    pl_in.add_output(lambda data: print(data))

    if vis:
        filter1 =Transform_filter(name="Raw Filter", names=channel_names_raw)
        pl_in.add_output(filter1)
        pl_in.add_output(filter1, data_stream="Channel Names", recv_name="receive_channels")

        draw_raw = Draw_lines(name='Raw Data', n_plots=len(channel_names_raw), xAxisLength=x_raw)
        filter1.add_output(draw_raw)
        filter1.add_output(draw_raw, data_stream="Channel Names", recv_name="receive_channels")

    window = Transform_window(100, 0)
    pl_in.add_output(window)

    fts = Transform_feature(features=['calc_mean', 'rms'], feature_args={"samplingfrequency": meta['sample_rate']})
    window.add_output(fts)
    pl_in.add_output(fts, data_stream="Channel Names", recv_name="receive_channels")

    if vis:
        filter2 =Transform_filter(name="Feature Filter", names=channel_names_fts)
        fts.add_output(filter2)
        fts.add_output(filter2, data_stream="Channel Names", recv_name="receive_channels")

        draw_fts = Draw_lines(name='Features', n_plots=len(channel_names_fts), xAxisLength=x_processed)
        filter2.add_output(draw_fts)
        filter2.add_output(draw_fts, data_stream="Channel Names", recv_name="receive_channels")

    to_fs = Biokit_to_fs()
    fts.add_output(to_fs)

    norm = Biokit_norm()
    to_fs.add_output(norm)

    if vis:
        from_fs = Biokit_from_fs()
        norm.add_output(from_fs)

        filter3 =Transform_filter(name="Normed Feature Filter", names=channel_names_fts)
        from_fs.add_output(filter3)
        fts.add_output(filter3, data_stream="Channel Names", recv_name="receive_channels")

        draw_normed = Draw_lines(name='Normed Features', n_plots=len(channel_names_fts), ylim=(-5, 5), xAxisLength=x_processed)
        filter3.add_output(draw_normed)
        filter3.add_output(draw_normed, data_stream="Channel Names", recv_name="receive_channels")

    return norm


def add_recognition(norm, x_raw, x_processed, vis=True):
    recog = Biokit_recognizer(model_path="./models/KneeBandageCSL2018/partition-stand/sequence/", token_insertion_penalty=50)
    norm.add_output(recog)

    draw_recognition_path = Draw_recognition(xAxisLength=[x_processed, x_processed, x_processed, x_raw])
    recog.add_output(draw_recognition_path)
    recog.add_output(draw_recognition_path, data_stream='Meta', recv_name='receive_meta')

    memory = Memory(x_raw)
    pl.add_output(memory, data_stream='Annotation')
    memory.add_output(draw_recognition_path, recv_name='receive_annotation')

    return recog


def add_train(norm):
    pass

def save(pl, file):
    print('--- Save Pipeline ---')
    pl.save(file)


    print('--- Load Pipeline ---')
    pl_val = Node.load(file)

    # TODO: validate & test pipeline
    # print()

    print('--- Visualize Pipeline ---')
    pl.make_dot_graph().save(file.replace('.json', '.png'))


if __name__ == "__main__":
    channel_names_raw = ['EMG1', 'Gonio2', 'AccLow2']
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

    print('=== Build Processing Pipeline ===')

    # TODO: currently the saving and everything else assumes we have a single node as entry, not sure if that is always true. consider multi indepdendent sensors, that are synced in the second node 
    #   -> might be solveable with "pipeline nodes" or similar, where a node acts as container for a node system -> might be good for paralellisation anyway 
    pl = In_playback(files="./data/KneeBandageCSL2018/part00/01.h5", meta=meta, batch=20)
    # pl = Playback(files="./data/KneeBandageCSL2018/**/*.h5", meta=meta, batch=20)

    norm = add_processing(pl, x_raw=x_raw, x_processed=x_processed, vis=True)
    save(pl, "pipelines/preprocess.json")


    print('=== Build Recognition Pipeline ===')

    recog = add_recognition(norm, x_raw=x_raw, x_processed=x_processed, vis=True)
    save(pl, "pipelines/recognize.json")



    # print('=== Build Train Pipeline ===')

    # pl = In_data(files="./data/KneeBandageCSL2018/part00/01.h5", meta=meta, batch=20)
    # norm = add_processing(pl, x_raw=x_raw, x_processed=x_processed, vis=False)
    # train = add_train(norm)
    # save(train, "pipelines/train.json")