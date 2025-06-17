from livenodes import Node, Graph
import multiprocessing as mp

import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
def f(): print("child running")

if __name__ == "__main__":
    mp.set_start_method('spawn', force=True)  # Use 'fork' for macOS compatibility
    mp.log_to_stderr(logging.DEBUG)
    mp.get_logger().setLevel(logging.DEBUG)
    n = Node.load("/Users/yale/Repositories/HAR-Dataset-Combination/data_prep_ln/graphs/fps_test_simple.yml")
    g = Graph(start_node=n)
    g.run_in_script()

    # p = mp.Process(target=f)
    # print("about to start")
    # p.start()
