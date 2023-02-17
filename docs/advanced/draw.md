# Draw System

Every node may choose to implement a draw/interactive frontend.
Each node may choose what to draw. This can either be data in form of plots, information in form of text or even controls, like playback speed etc. At the moment only a matplotlib frontend is implemented, but any qt based frontend will be possible in the future.

Note, that the way to implement the draw functionality is by inheriting from teh viewer class.
The node then implements a drw_init funciton, which gets passed tyhe canvas to draw on. Do not xreate your own as that will not be embedded properly. The init funciton returns an update funciton which may acess the scope of its parent function (ie draw_init). and will be called on every matplotlib animation update with the last stored draw state (draw data) from emit_draw. This might be exactly the same as before (ie if the animation update is called more frequently thant the draw_emit)!


updates are called in the main process while processing is called in the nodes process (see multiprocessing.md). Qt currently does not elegantly support multiprocess drawing. 

for best performances with matplotlib smart uses blit=true. therefore, make sure to return all matplotlib artists, that should be in the foreground and/or are updated in your uptate function.


at the moment the draw functionality would work without qt only using matplotlib.
Note, that this might not be available in the future, as user resizing will only be available in qt and faster rendering backends might not be compatible with matplotlib. For support of as many hardwares as possible we will try to further support this option in the futrue, but no guarantees.