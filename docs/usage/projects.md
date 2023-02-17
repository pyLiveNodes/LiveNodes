# Projects

A project is a scope for multiple files and graphs/pipelines.
A project is required to have the following subfolders:
- data: all data will live here, ie data from another dataset and/or recorded data, etc.
    - if you want to work with data from another datasource it is recommended to store the full original and create a pipeline to transform it into the smart structure and save it parallel to the original data. If the original data changes or you want to manipulate it, you then just may re-run the pipeline.
- gui: do not touch, this stores gui information like layout or images of your piplines
- models: contains serialized ml model, in case of biokit this will be multiple files. 
    - please consider to not use pickled models as they might be security hazards (see blog:), hard to reprocue and evern harder to analyse. Ratehr use serialization functions that only store the learned parameters. you'll get versioning and tests for incompatibility for free.
- pipelines: contains all your graphs/pipeliens, may be created using the python or gui interface
- nodes: not yet implemented, will contain project specific nodes (ie transformer nodes to re-format datasets). If your node is clean and documented, please consider creating a merge request for the main repo (see: mrs/contributing)
- info.json currently unused, will be used for project meta information