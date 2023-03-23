# Draw System

Every node may choose to implement a draw/interactive frontend.
Each node may choose what to draw. This can either be data in form of plots, information in form of text or even controls, like playback speed etc. At the moment Matplotlib QT and Vispy based frontends are implemented, just inherit from the appropriate `View_<>` class. 

Here is an example from the Matplotlib package. It follows most of the standard Node aspects, declaring ports, category etc. The key interfaces are the `process` and `_init_draw` methods: `process` receives all data passed in via the connecting ports and `_init_draw` is responsible to initialize the passed subfigure.

In this case `process` does no procesing itself and just passes the data to the drawing portion of the node. `_init_draw` receives the subfigure it will be drawing on and may set it up as needed. It then needs to return an update function, whos task is to update the canvas based on the received inputs. It returns the changed elements of the subfigure, which will be used in blitting and is responsible for making Matplotlib capable of realtime rendering. Simply out, blitting only redraws these elements keeping the background in memory. If you can avoid updating the axis scale and update as little in the graph as possible, then you'll see the best performance. 

Note, that `process` and `_init_draw`/`update` are likely called in separate processes. Smart-Studio for instance uses separate processes in order to keep the render and interface snapy even if heavy calculations take place.

```
class Draw_heatmap(View_MPL):
    ports_in = Ports_in()
    ports_out = Ports_empty()

    category = "Draw"
    description = ""

...

    def _init_draw(self, subfig):
        subfig.suptitle(self.name, fontsize=14)
        ax = subfig.subplots(1, 1)
        
        if not self.disp_ticks:
            ax.set_yticks([])
            ax.set_xticks([])

        mesh = None
        zlim = self.zlim

        def update(data):
            nonlocal zlim, mesh

            if mesh == None:
                mesh = ax.pcolormesh(data, cmap="YlGnBu", vmax=zlim, vmin=0)
            else:
                mesh.set_array(data)

            # return image elements that changed. This is used in blitting and is what makes this 20/30 times faster.
            return [mesh]

        return update

    def process(self, data,  **kwargs):  
        # only every draw the last batch
        # since no history is displayed we also don't need to keep it
        self._emit_draw(data=data)
```