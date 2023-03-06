from .bridge_abstract import Bridge

from .bridge_local import Bridge_local
from .bridge_thread import Bridge_thread
from .bridge_process import Bridge_process

### IMPORTANT: the aio bridges are faster (threads) or as fast (processes) as the above implementations. However, i don't know why the feeder queues are not closed afterwards leading to multiple undesired consequences (including a broken down application)
# THUS => only re-enable these if you are willing to debug and test that!
# from .bridge_thread_aio import Bridge_thread_aio
# from .bridge_process_aio import Bridge_process_aio


from .mp_data_storage import Multiprocessing_Data_Storage