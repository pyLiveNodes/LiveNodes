import importlib
import multiprocessing as mp
import sys
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy

from livenodes.gui.home import Home
from livenodes.gui.config import Config
from livenodes.gui.run import Run
from livenodes.core.node import Node
from livenodes.core import global_registry

from livenodes.core.logger import logger

import datetime
import time
import os
import json



class SubView(QWidget):

    def __init__(self, child, name, back_fn, parent=None):
        super().__init__(parent)

        # toolbar = self.addToolBar(name)
        # toolbar.setMovable(False)
        # home = QAction("Home", self)
        # toolbar.addAction(home)

        button = QPushButton("Back")
        button.setSizePolicy(QSizePolicy())
        button.clicked.connect(back_fn)

        toolbar = QHBoxLayout()
        toolbar.addWidget(button)
        toolbar.addStretch(1)
        toolbar.addWidget(QLabel(name))

        l1 = QVBoxLayout(self)
        l1.addLayout(toolbar)
        l1.addWidget(child)

        self.child = child

    def stop(self):
        if hasattr(self.child, 'stop'):
            self.child.stop()


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, parent=None, projects='./projects/*'):
        super(MainWindow, self).__init__(parent)

        self.central_widget = QtWidgets.QStackedWidget()
        self.setCentralWidget(self.central_widget)

        print(projects)
        self.widget_home = Home(onconfig=self.onconfig,
                                onstart=self.onstart,
                                projects=projects)
        self.central_widget.addWidget(self.widget_home)

        self.log_file = None

        self.home_dir = os.getcwd()
        print('CWD:', os.getcwd())

        self._save_dict = {}
        if os.path.exists('smart-state.json'):
            with open('smart-state.json', 'r') as f:
                self._save_dict = json.load(f)

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
        with open('smart-state.json', 'w') as f:
            json.dump(self._save_dict, f, indent=2)

        return super().closeEvent(event)

    def _set_state(self, view):
        print(view)
        if hasattr(view,
                   'set_state') and view.__class__.__name__ in self._save_dict:
            view.set_state(**self._save_dict[view.__class__.__name__])

    def _save_state(self, view):
        if hasattr(view, 'get_state'):
            self._save_dict[view.__class__.__name__] = view.get_state()

    def return_home(self):
        cur = self.central_widget.currentWidget()

        # TODO: this shoudl really be in a onclose event inside of config rather than here..., but i don't know yet when/how those are called or connected to...
        if isinstance(cur.child, Config):
            cur.child.save()
            # vis_state, new_pl = cur.child.get_nodes()
            # print(vis_state)
            # for n in cur.child.get_nodes().values():
            #     print(n.__getstate__())

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
        widget_run = SubView(child=Run(pipeline=pipeline),
                             name=f"Running: {pipeline_path}",
                             back_fn=self.return_home)
        self.central_widget.addWidget(widget_run)
        self.central_widget.setCurrentWidget(widget_run)

        self._set_state(widget_run)

    def onconfig(self, project_path, pipeline_path):
        os.chdir(project_path)
        print('CWD:', os.getcwd())

        pipeline = Node.load(pipeline_path)
        widget_run = SubView(child=Config(pipeline=pipeline,
                                          node_registry=global_registry,
                                          pipeline_path=pipeline_path),
                             name=f"Configuring: {pipeline_path}",
                             back_fn=self.return_home)
        self.central_widget.addWidget(widget_run)
        self.central_widget.setCurrentWidget(widget_run)

        self._set_state(widget_run)


if __name__ == '__main__':
    # === Load environment variables ========================================================================
    import os
    from dotenv import dotenv_values
    import json

    config = {
        **dotenv_values(".env"),  # load shared development variables
        # **dotenv_values(".env.secret"),  # load sensitive variables
        **os.environ,  # override loaded values with environment variables
    }

    env_projects = config.get('PROJECTS', './projects/*')
    env_modules = json.loads(config.get('MODULES', '[ "livenodes.nodes", "livenodes.plux"]'))

    print('Procects folder: ', env_projects)
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

    script_dir = os.path.dirname(__file__) #<-- absolute dir the script is in
    rel_path = "livenodes/gui/static/style.qss"
    abs_file_path = os.path.join(script_dir, rel_path)
    with open(abs_file_path, 'r') as f:
        app.setStyleSheet(f.read())

    window = MainWindow(projects=env_projects)
    window.resize(1400, 820)
    window.show()
    sys.exit(app.exec())
