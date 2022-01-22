Device Node (RIoT)
- input: None
- output: 2d numpy array (time, channels) + meta info (channel names)
- setup: device id, frame rate (no filter -> should be its own node)
- settings (runtime): channel select for plot, plot length
- visualizations: raw data, 

Replay Node
- input: None
- output: 2d numpy array (time, channels)
- setup: data path
- settings (runtime): channel select for plot, plot length, replay speed
- visualizations: raw data, replay dials

Save Node
- input: 2d numpy array (time, channels)
- output: None
- setup: data path
- settings (runtime): None
- visualizations: None

Annotation Node (Channel)
- input: 2d numpy array (time, channels)
- output: 2d numpy array + annotation ?
- setup: channel selection
- settings: None
- visualizations: None

Annotation Node (Digital Button)
- input: 2d numpy array (time, channels)
- output: 2d numpy array + annotation ?
- setup: mode (push to talk / push to trigger, etc)
- settings: None
- visualizations: Buttons

Preprocessing Node (Windowing)
- input: 2d numpy array (time, channels)
- output: 2d numpy array (time, channels)
- setup: length, overlap, function
- settings: None
- visualizations: None / Window Borders

Preprocessing Node (Avg/Feature)
- input: 2d numpy array (time, channels)
- output: 2d numpy array (time, features)
- setup: feature hyperparameters
- settings: None
- visualizations: Processing output

Recognition Node (Sequence HMM)
- input: 2d numpy array (time, features)
- output: sequence of words (maybe multiple levels)
- setup: model_path (+ hyperparameters that may be overwritten)
- settings: None
- visualizations: Recognition, Search Graph, GMMs, ...