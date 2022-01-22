from src.nodes.playback import Playback

pl = Playback(files="./data/KneeBandageCSL2018/**/*.h5", sample_rate=1000)

pl.add_output(lambda data: print(data))

pl.start_processing()