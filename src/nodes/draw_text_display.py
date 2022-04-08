from .node import View

class Draw_text_display(View):
    """
    Draws any given Text replacing previosly drawn text.
    
    Draws on a matplotlib canvas.
    """

    channels_in = ['Text']
    channels_out = []

    category = "Draw"
    description = "" 

    example_init = {
        "name": "Text Outpuy",
        "initial_text": "",
    }

    def __init__(self, initial_text="", name = "Text Output", **kwargs):
        super().__init__(name=name, **kwargs)

        self.text = initial_text


    def _init_draw(self, subfig):
        subfig.suptitle(self.name, fontsize=14)
        ax = subfig.subplots(1, 1)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.set_xticks([])
        ax.set_yticks([])

        label = ax.text(0.005, 0.95, self.text, zorder=100, fontproperties=ax.xaxis.label.get_font_properties(), rotation='horizontal', va='top', ha='left', transform = ax.transAxes)
        old_text = self.text

        def update (text=None):
            nonlocal label, old_text

            old_text = text

            # TODO: confidentelly assume that at some point we get the "only return label reference if it actually changed" to work (currenlty this causes troubles with matplotlib)
            # if old_text != text:
            label.set_text(text)

            return [label]
        return update

    def process(self, text, **kwargs):
        self._emit_draw(text=text)  
