import time
import datetime
import h5py
import json
import os

from livenodes.core.node import Node, Location

from . import local_registry


@local_registry.register
class Out_data(Node):
    channels_in = ['Data', 'Channel Names', 'Meta', 'Annotation']
    channels_out = []

    category = "Save"
    description = ""

    example_init = {'name': 'Save', 'folder': './data/Debug/'}

    def __init__(self, folder, name="Save", compute_on=Location.PROCESS, **kwargs):
        super().__init__(name, compute_on=compute_on, **kwargs)

        self.folder = folder

        if not os.path.exists(self.folder):
            os.makedirs(self.folder)

        # NOTE: we can create the filename here (although debatable)
        # but we cannot create the file here, as no processing is being done or even planned yet (this might just be create_pipline)
        self.outputFilename = f"{self.folder}{datetime.datetime.fromtimestamp(time.time())}"
        print("Saving to:", self.outputFilename)

        self.outputFile = None
        self.outputDataset = None

        self.outputFileAnnotation = None
        self.last_annotation = None

        self.channels = None

    def _settings(self):
        return {\
            "folder": self.folder
        }

    def _onstart(self):
        self.outputFile = h5py.File(self.outputFilename + '.h5', 'w')
        self.outputFileAnnotation = open(f"{self.outputFilename}.csv", "w")
        self.outputFileAnnotation.write("start,end,act\n")
        self.info('Created Files')

    def _onstop(self):
        self.outputFile.close()
        if self.last_annotation is not None:
            self.outputFileAnnotation.write(
                f"{self.last_annotation[1]},{self.last_annotation[2]},{self.last_annotation[0]}"
            )
        self.outputFileAnnotation.close()
        self.info('Stopped writing out and closed files')

    def _should_process(self,
                        data=None,
                        channel_names=None,
                        meta=None,
                        annotation=None):
        return data is not None and \
            (self.channels is not None or channel_names is not None)

    def process(self,
                data,
                channel_names=None,
                meta=None,
                annotation=None,
                **kwargs):

        if channel_names is not None:
            self.channels = channel_names

            m_dict = self._read_meta()
            m_dict['channels'] = channel_names
            self._write_meta(m_dict)

            if self.outputDataset is None:
                self.outputDataset = self.outputFile.create_dataset(
                    "data", (1, len(self.channels)),
                    maxshape=(None, len(self.channels)),
                    dtype="float32")

        if meta is not None:
            m_dict = self._read_meta()
            for key, val in meta.items():
                # We'll assume that the channels are always hooked up
                if key != "channels":
                    m_dict[key] = val
            self._write_meta(m_dict)

        if annotation is not None:
            self.receive_annotation(annotation)

        self.outputDataset.resize(self.outputDataset.shape[0] + len(data),
                                  axis=0)
        self.outputDataset[-len(data):] = data

    def receive_annotation(self, data_frame, **kwargs):
        # For now lets assume the file is always open before this is called.
        # TODO: re-consider that assumption
        if self.last_annotation is None:
            self.last_annotation = (data_frame[0], 0, 0)

        for annotation in data_frame:
            if annotation == self.last_annotation[0]:
                self.last_annotation = (annotation, self.last_annotation[1],
                                        self.last_annotation[2] + 1)
            else:
                # self.verbose(f"writing: {self.last_annotation[1]},{self.last_annotation[2]},{self.last_annotation[0]}")
                self.outputFileAnnotation.write(
                    f"{self.last_annotation[1]},{self.last_annotation[2]},{self.last_annotation[0]}\n"
                )
                self.last_annotation = (annotation,
                                        self.last_annotation[2] + 1,
                                        self.last_annotation[2] + 1)

    def _read_meta(self):
        if not os.path.exists(f"{self.outputFilename}.json"):
            return {}
        with open(f"{self.outputFilename}.json", 'r') as f:
            return json.load(f)

    def _write_meta(self, setting):
        with open(f"{self.outputFilename}.json", 'w') as f:
            json.dump(setting, f, indent=2)
