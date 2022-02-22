import numpy as np
import multiprocessing as mp

from .node import Node

from matplotlib.widgets import TextBox, Button

class Annotate_ui_button(Node):
    def __init__(self, fall_back_target="Unknown", name = "GUI Button Annotation", dont_time = False):
        super().__init__(name=name, dont_time=dont_time)

        self.target_q = mp.Queue()
        self.fall_back_target = fall_back_target
        
        self.annot_target = "Test"
        self.current_target = fall_back_target
        self.recording = False

    @staticmethod
    def info():
        return {
            "class": "Annotate_ui_button",
            "file": "Annotate_ui_button.py",
            "in": ["Data"],
            "out": ["Data", "Annotation"],
            "init": {
                "name": "Name"
            },
            "category": "Annotation"
        }
    
    def _get_setup(self):
        """
        Get the Nodes setup settings.
        Primarily used for serialization from json files.
        """
        return { \
            "name": self.name,
            "fall_back_target": self.fall_back_target
        }
    
        
    @property
    def in_map(self):
        return {
            "Data": self.receive_data
        }

    def receive_data(self, data_frame, **kwargs):
        # IMPORTANT: we assume that the length of data_frame is always short enough that we do not care about timing issues with the label
        self.send_data(data_frame)

        while not self.target_q.empty():
            self.fall_back_target, self.current_target = self.target_q.get()

        self.send_data([self.current_target] * len(data_frame), data_stream="Annotation")
        

    def __activity_toggle_rec(self, event):
        if self.recording:
            # Stop recording 
            self.bnext.label.set_text('Start')
            self.target_q.put((self.fall_back_target, self.fall_back_target))
        else:
            # Start recording
            self.bnext.label.set_text('Stop')
            self.target_q.put((self.fall_back_target, self.annot_target))

        self.recording = not self.recording

    def __update_fallback(self, text):
        self.fall_back_target = text
        self.target_q.put((self.fall_back_target, self.annot_target))

    def __update_annot(self, text):
        self.annot_target = text

    def init_draw(self, subfig):
        subfig.suptitle("Annotate", fontsize=14)

        self.axes = subfig.subplots(3, 1, sharex=True)

        self.target_default = TextBox(self.axes[0], 'Fallback:', initial=self.fall_back_target)
        # self.target_default.label.set_fontsize(20)
        self.target_default.on_submit(self.__update_fallback)

        self.target_annotate = TextBox(self.axes[1], 'Recognize:', initial=self.annot_target)
        # self.target_annotate.label.set_fontsize(20)
        self.target_annotate.on_submit(self.__update_annot)

        self.bnext = Button(self.axes[2], 'Start')
        self.bnext.label.set_fontsize(20)
        self.bnext.on_clicked(self.__activity_toggle_rec)

        def update (**kwargs):
            nonlocal self
            return self.axes

        return update