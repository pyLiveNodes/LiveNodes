import sys
import traceback
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy

from livenodes.gui.home import Home
from livenodes.gui.config import Config
from livenodes.gui.run import Run
from livenodes.gui.pages.parent_page import Parent
from livenodes.core.node import Node
from livenodes.core import global_registry

from livenodes.core.logger import logger

import datetime
import time
import os

from state import State


def noop(*args, **kwargs):
    pass

class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, state_handler, parent=None, projects='./projects/*', home_dir=os.getcwd(), _on_close_cb=noop):
        super(MainWindow, self).__init__(parent)

        self.central_widget = QtWidgets.QStackedWidget()
        self.setCentralWidget(self.central_widget)

        self.widget_home = Home(onconfig=self.onconfig,
                                onstart=self.onstart,
                                projects=projects)
        self.central_widget.addWidget(self.widget_home)

        self.log_file = None

        self.home_dir = home_dir
        print('Home Dir:', home_dir)
        print('CWD:', os.getcwd())

        self._on_close_cb = _on_close_cb


        self.state_handler = state_handler

        # for some fucking reason i cannot figure out how to set the css class only on the home class... so hacking this by adding and removign the class on view change...
        # self.central_widget.setProperty("cssClass", "home")
        # self.widget_home.setProperty("cssClass", "home")
        self._set_state(self.widget_home)

    def stop(self):
        cur = self.central_widget.currentWidget()
        if hasattr(cur, 'stop'):
            cur.stop()

        if self.log_file is not None:
            logger.remove_cb(self._log_helper)
            self.log_file.close()
            self.log_file = None

    def closeEvent(self, event):
        self.stop()

        os.chdir(self.home_dir)
        print('CWD:', os.getcwd())

        self._save_state(self.widget_home)
        self._on_close_cb()

        return super().closeEvent(event)

    def _set_state(self, view):
        if hasattr(view,
                   'set_state') and self.state_handler.val_exists(view.__class__.__name__):
            view.set_state(**self.state_handler.val_get(view.__class__.__name__))

    def _save_state(self, view):
        if hasattr(view, 'get_state'):
            self.state_handler.val_set(view.__class__.__name__, view.get_state())

    def return_home(self):
        cur = self.central_widget.currentWidget()
        self._save_state(cur)
        self.stop()
        self.central_widget.setCurrentWidget(self.widget_home)
        self.central_widget.removeWidget(cur)
        print("Nr of views: ", self.central_widget.count())
        os.chdir(self.home_dir)
        print('CWD:', os.getcwd())

    def _log_helper(self, msg):
        self.log_file.write(msg + '\n')
        self.log_file.flush()

    def onstart(self, project_path, pipeline_path):
        os.chdir(project_path)
        print('CWD:', os.getcwd())

        log_folder = './logs'
        log_file = f"{log_folder}/{datetime.datetime.fromtimestamp(time.time())}"

        if not os.path.exists(log_folder):
            os.mkdir(log_folder)

        self.log_file = open(log_file, 'a')
        logger.register_cb(self._log_helper)

        pipeline = Node.load(pipeline_path)
        # TODO: make these logs project dependent as well
        widget_run = Parent(child=Run(pipeline=pipeline),
                             name=f"Running: {pipeline_path}",
                             back_fn=self.return_home)
        self.central_widget.addWidget(widget_run)
        self.central_widget.setCurrentWidget(widget_run)

        self._set_state(widget_run)

    def onconfig(self, project_path, pipeline_path):
        os.chdir(project_path)
        print('CWD:', os.getcwd())

        pipeline = Node.load(pipeline_path)
        widget_run = Parent(child=Config(pipeline=pipeline,
                                          node_registry=global_registry,
                                          pipeline_path=pipeline_path),
                             name=f"Configuring: {pipeline_path}",
                             back_fn=self.return_home)
        self.central_widget.addWidget(widget_run)
        self.central_widget.setCurrentWidget(widget_run)

        self._set_state(widget_run)



def main():
    # === Load environment variables ========================================================================
    import os
    import shutil
    from dotenv import dotenv_values
    import json

    home_dir = os.getcwd()

    path_to_state = os.path.join(home_dir, 'smart-state.json')
    try:
        smart_state = State.load(path_to_state)
    except Exception as err:
        print(f'Could not open state, saving file and creating new ({path_to_state}.backup)')
        print(err)
        print(traceback.format_exc())
        shutil.copyfile(path_to_state, f"{path_to_state}.backup")
        smart_state = State({})
        
    env_vars = {key.lower(): val for key, val in {
        **dotenv_values(".env"),
        **os.environ
    }.items() if key in ['PROJECTS', 'MODULES']}

    smart_state.val_merge(env_vars)

    env_projects = smart_state.val_get('projects', './projects/*')
    env_modules = json.loads(smart_state.val_get('modules', '[ "livenodes.nodes", "livenodes.plux"]'))

    print('Projects folder: ', env_projects)
    print('Modules: ', env_modules)

    # === Fix MacOS specifics ========================================================================
    # this fix is for macos (https://docs.python.org/3.8/library/multiprocessing.html#contexts-and-start-methods)
    # TODO: test/validate this works in all cases (ie increase test cases, coverage and machines to be tested on)
    # mp.set_start_method(
    #     'fork',
    #     force=True)  # force=True doesn't seem like a too good idea, but hey
    # mp.set_start_method('fork')

    # === Load modules ========================================================================
    global_registry.collect_modules(env_modules)

    # === Setup application ========================================================================
    app = QtWidgets.QApplication([])
    # print(smart_state)
    # print(smart_state.space_get('views'))
    def onclose():
        smart_state.val_set('window_size', (window.size().width(), window.size().height()))
        smart_state.save(path_to_state)

    
    window = MainWindow(state_handler=smart_state.space_get('views'), projects=env_projects, home_dir=home_dir, _on_close_cb=onclose)
    # TODO: store the old size in state.json and re-apply here...
    window.resize(*smart_state.val_get('window_size', (1400, 820)))
    window.show()

    # chdir because of relative imports in style.qss ....
    script_dir = os.path.dirname(__file__) #<-- absolute dir the script is in
    os.chdir(script_dir)
    with open("./livenodes/gui/static/style.qss", 'r') as f:
        app.setStyleSheet(f.read())
    os.chdir(home_dir)

    sys.exit(app.exec())

if __name__ == '__main__':
    main()
