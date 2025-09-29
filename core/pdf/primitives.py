# core/pdf/primitives.py
from reportlab.platypus import Flowable

class HR(Flowable):
    """Linha horizontal fina usada para indicar corte/continuação."""
    def __init__(self, width, thickness=0.6, pad_top=1, pad_bottom=1):
        super().__init__()
        self.width = width
        self.thickness = thickness
        self.pad_top = pad_top
        self.pad_bottom = pad_bottom
        # altura total do flowable (considerando pads)
        self.height = float(self.pad_top + self.thickness + self.pad_bottom)

    def wrap(self, aW, aH):
        return (self.width, self.height)

    def draw(self):
        c = self.canv
        c.saveState()
        x0 = 0
        x1 = self.width
        y = self.pad_bottom
        c.setLineWidth(self.thickness)
        c.line(x0, y, x1, y)
        c.restoreState()
